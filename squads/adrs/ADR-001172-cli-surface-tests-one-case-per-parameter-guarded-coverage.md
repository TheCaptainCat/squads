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
description: 'CLI tests in-process on the bundled spec: one case per parameter, shared
  registrations tested once, a marker-based coverage guard'
created_at: '2026-10-27T21:25:41Z'
updated_at: '2026-10-28T00:37:18Z'
---
<!-- sq:body -->
## Context

The repository keeps only its `tests/meta` guards and the shared helpers: `tests/_squads.py` (a squad built once per module, copied per test), `tests/_help_tree.py` (a walk of the live Typer command tree), `tests/_helpers.py`, `tests/conftest.py` and the root `conftest.py`. The previous suite reached about 16,000 tests and about 50 minutes on the Windows CI runner. Most of that volume came from cross products of parametrised tables (position x shape x layer), and the same seam was asserted at several layers.

The first tests to rebuild are CLI tests: every command, every parameter, run against the engine and the bundled spec. Measured on 2026-10-27, outside any squad (bundled vocabulary), with `_help_tree.command_nodes()`:

- 344 commands (groups included), 267 leaf commands, 1,079 (command, parameter) pairs counting group callbacks.
- The nine work-item groups come from one builder, `build_item_app`. Each has 11 verbs, plus 3 more on a type that hosts a sub-entity kind (`add-<kind>`, `<kind>`, the plural listing). `retype` and `remove` exist only on non-roster types.
- The comment verbs come from one registrar, `register_comment_verbs`, and are mounted on every item group, every sub-entity group and the `role`, `skill` and `operator` groups.
- `sq create <type>` takes the same options on eight types. `guide` differs: it takes `--tag` and `--tech`, and has no `--label`, `--priority` or `--ref`.
- Sub-entity verbs take the same options on all three bundled kinds, except `subtask update --story/--no-story` and `finding update --severity/--deferred-to`.
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

- **Work-item verbs** are tested on the bundled `task` type. It is non-roster, so it has `retype` and `remove`. It hosts a sub-entity kind (`subtask`) whose `--story` option resolves against another item (its parent feature's stories). It also carries a parent rule that `sq check` enforces. No other bundled type exercises more of the builder.
- **Sub-entity verbs** are tested on `task subtask`. A parameter that only some kinds carry is tested on a host that carries it: `--severity` and `--deferred-to` on `review finding`.
- **Comment verbs** are tested on the `task` item host. Addressing through the other host kinds is tested once each: sub-entity, role, skill and operator. Each of those cases covers the address, not the verb's parameters again.
- **`sq create <type>`** is tested on `task`. A parameter only some types carry is tested on a type that carries it: `--tag` and `--tech` on `guide`.
- **Per-type differences that the spec decides**, such as which transitions a lifecycle allows, are not CLI surface. The `status` verb is tested on `task`'s lifecycle: one allowed transition and one refused transition. Whether every bundled lifecycle is well formed is the spec loader's concern, not this suite's.

The verb-set guard is a new `tests/meta` module. It enumerates the tree with `_help_tree.command_nodes()` and reads the bundled spec. For every declared work-item type it asserts two things:

- The type's verb set equals the reference type's verb set, minus what the spec decides: the `add-<kind>`, `<kind>` and plural verbs are present exactly when the type hosts a kind, and `retype`/`remove` are present exactly when the type is not roster.
- Each verb's parameter names equal the reference type's, except the parameters derived from the type's own declarations: create-time attributes and the kind-specific sub-entity options.

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
- **Parameter name.** An option is named by its first long flag (`--title`); its short alias is not a separate parameter. An argument is named as the usage line prints it (`N`, `TITLE`), which is Click's `human_readable_name`.
- **Every leaf command is declared**, not only every (command, parameter) pair. A leaf with no parameters (`sync`, `ui`, `migrate up`) is declared with its command key alone: `@pytest.mark.covers("sync")`.
- **One marker, several parameters**, is only for an interaction (rule 1). A test may carry several `covers` markers when it asserts each one's effect.

The **coverage guard** is a new `tests/meta` module:

- It enumerates the tree with `_help_tree.command_nodes()` in an empty directory (bundled vocabulary), hidden parameters included, folding each node onto its key as above.
- It reads every `covers` marker from the CLI test modules with `ast`, without importing them.
- It fails, listing them, when a pair or a leaf command of the tree is declared by no test.
- It also fails when a marker names a pair or a key the tree no longer has (stale).
- It excludes only parameters squads does not declare: Typer's `--install-completion` and `--show-completion`. Click's `--help` is not a parameter of the tree, and the help-rule guard already holds it. The exclusion is a named constant in the guard, one reason per entry.

The marker is checked against what the test runs. The CLI `invoke` fixture resolves each argument list against the live tree and records the keys and (key, parameter) pairs it reached. At teardown it fails the test when a declared key or pair is not among them. A marker cannot claim coverage its test does not exercise. This check is local to the test, so `-k`, `--lf` and xdist runs stay valid.

The guard proves that each pair has a test. It does not prove that the test fails when the parameter breaks. That proof is made once, when the test is written: break the parameter's effect, see the test go red, restore it. Review checks that this was done.

### 4. In-process, on a copied squad

Every CLI test runs `sq` in-process through Typer's `CliRunner` (the `runner`/`invoke` fixtures). It runs on its own copy of a squad built once per module (`copy_squad` and the builders in `tests/_squads.py`), under the frozen clock. No test starts a subprocess. A behaviour that is only observable in a separate process, such as the console-script entry point or environment latching at interpreter start, is outside this suite. The autouse fixtures in `tests/conftest.py` stay in force for every test: the context reset, the plain-output environment, the empty starting directory and the item-file write ledger.

### 5. Assert what the user sees

A case asserts the exit code and the composed output: the whole message line or the JSON object, not a substring that would survive a wrong message. State is read back through the CLI: `sq <type> <n> show --json`, or the `--json` form of the listing or command concerned. A test never opens an item file or `.squads.json`. A test reads a file directly only when that file is the output the command under test produces for the user: the generated agent-facing files (`.claude/` pointers, the managed `CLAUDE.md` and `AGENTS.md` regions) written by `init`, `adopt`, `sync` and the roster verbs that regenerate pointers, and the override files that `sq override` scaffolds or restamps. No other file is read; any other state goes through the CLI. A test writes an item file or `.squads.json` directly only to arrange a state that no CLI path can produce (a corrupt, legacy or drifted corpus for `repair`, `check`, `migrate`, `adopt` or `renumber`); its assertions still read state through the CLI.

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

### Scope: bundled spec only

This suite runs against the engine with the bundled workflow spec, playbook and role catalog, and no project override. Behaviour under a custom-vocabulary override is outside its scope. The keys are type-agnostic (`<type>`, `<kind>`, `<host>`) so that a later override-backed run can be added as a second squad build and declare against the same keys, without renaming anything.

### Regression tests

Specific regression tests, one per verified bug, are a separate set in `tests/regressions/`. They follow the same rules for execution (rule 4), assertion (rule 5) and naming: each module and test is named for the behaviour the bug broke, never by its ticket. A regression test carries no `covers` marker. It neither counts toward nor replaces surface coverage, and a surface case is not removed because a regression test touches the same parameter. Each one is shown red against the unfixed code before it is kept. Their organisation beyond that is left to when they are written.

### Time bound

Every CI test job runs in under 10 minutes; Windows, running the full suite, in at most 15. A target is met on an OS when every one of at least two runs on that OS is under it. There is no test-count ceiling and no row-budget guard: the time targets are the only bound, and review checks for cross products and duplicated cases.

## Why

- Repetition across hosts of one registration was the largest multiplier. Folding it onto one host with a structural guard replaces about 700 repeated pairs with one assertion per host, and the guard is stronger: a missing verb on any type fails it, where a per-type test only fails for the types someone remembered to list.
- `task` is the bundled type that exercises the most of the builder: retype, remove, a sub-entity kind, a cross-item option and a parent rule. A smaller type would leave verbs untested on the reference host.
- A marker with literal arguments can be read without running the suite. The guard is then cheap, works under partial runs, and a contributor can predict it: add an option, add a test that names it. Inferring coverage from recorded invocations alone would require a whole-suite run to decide and fail spuriously under `-k` and xdist. The invoke-fixture check closes the hole a bare marker leaves: a marker that no invocation honours.
- One case per parameter grows linearly with the surface (about 374 pairs). An effect case plus a few refusals each gives on the order of 1,000 to 1,500 in-process tests, well inside the Windows target at the earlier per-test cost.
- Reading state through `show --json` keeps the tests on the user's contract. A storage-format change then does not break surface tests, and a broken `show` does not hide behind a direct file read.

## Consequences

- Two new `tests/meta` guards: verb-set parity across hosts, and (command, parameter) coverage. The `invoke` fixture gains the marker cross-check, and `covers` is registered as a pytest marker.
- Adding an option to any command fails the coverage guard until a test declares it. Adding a verb to the builder or a registrar fails nothing per type: one test on the reference host covers it, and the parity guard holds the rest.
- A new bundled type needs no new surface tests unless it brings a parameter of its own.
- Override-backed surface runs and the regression set are later work. Their keys and location are fixed here.
- The guards prove that a case exists, not that it is strong: a vacuous case is still caught by the falsification step and by review.

## Options considered and rejected

- **A per-type parametrised table for the generic verbs.** It reproduces the cross product this decision removes, and is weaker than the parity guard for types nobody added to the table.
- **The custom-vocabulary type from `_help_tree.py` as the reference host.** It would catch bundled-name literals in verb code, but those are already held by the `no_bundled_*_literal` guards. The suite's scope is the shipped spec.
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
<!-- sq:discussion:end -->
