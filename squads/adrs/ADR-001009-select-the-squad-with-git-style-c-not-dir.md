---
id: ADR-1009
sequence_id: 1009
type: decision
title: Select the squad with git-style -C, not --dir
status: Accepted
author: architect
refs:
- MILE-934:targets
- BUG-1008
- REV-995
- TASK-954
- ADR-1007
- ADR-263
description: -C runs sq as if started in PATH and walks up as ordinary use does; --dir
  is refused naming -C; the backwards inference goes away
created_at: '2026-10-15T19:17:11Z'
updated_at: '2026-10-15T20:17:28Z'
---
<!-- sq:body -->
## Context

Each claim is marked **read** (the source was read), **driven** (a command was run and its
output observed) or **inferred** (reasoned from read code, not exercised).

The operator ruled on 2026-10-15 (MILE-934, op-pierre, 2026-10-15T19:11:19Z): the global
`--dir`, which names a squad folder, is replaced by a git-style `-C <path>`, meaning "run `sq`
as if it had been started in `<path>`". It ships in 0.16. A comment at 2026-10-15T19:16:11Z
read `-C` as naming the project root with no walk-up; the operator corrected it at
2026-10-15T19:16:53Z: `-C` keeps the walk-up and refuses when no `.squads.toml` is found from
there. This decision settles how.

**Why `--dir` cannot be made sound.** Ordinary use walks up from the working directory to the
first `.squads.toml` and takes its `squad_dir` (`_paths.resolve`, read). `--dir` runs the other
way: given a squad folder, it has to infer which configuration owns it. REV-995 found that
inference wrong in nearly every layout it tried, each time letting a behind squad past the
schema gate with a synthesised configuration stamped at the package's own schema:

- F23 (driven by the reviewer): a project-root squad (`squad_dir = "."`), then `"./"`, a
  two-level `"work/squad"`, and `--dir` at the project root of a nested squad. `repair` and
  `migrate repad` rewrote a 0.14 corpus; `migrate up` said there was nothing to migrate.
- F26 (driven by the reviewer): a `squad_dir` outside its project tree (`"../shared"`, or an
  absolute path) is never on the walk up from the squad folder, so `--dir` there found no
  configuration at all.
- F27 and BUG-1008 (driven by the reviewer and QA): `sq init` never reads `--dir` and
  initialises the working directory.

Each fix so far closed the shapes it was shown. The working tree now walks up from the `--dir`
folder, accepts a configuration only when its root plus `squad_dir` resolves to that folder,
refuses a folder that holds squad data with no configuration above it, and still synthesises a
default configuration for a folder that holds none (`_paths.py:138-159`, read). That last
branch means a mistyped `--dir` runs commands on a phantom squad (inferred from the code). The
backwards inference is a second resolver beside the walk-up, and the gate is only as sound as
the weaker of the two.

**What the client does.** The VS Code extension never passes `--dir`. It spawns `sq` with the
workspace root as the working directory (`processRunner.ts`, `execFile(..., { cwd })`) and
mirrors only the walk-up branch to choose the folder it watches (`domain/squadDir.ts`,
`resolveSquadDir`); its doc comment says the `--dir` branch does not apply to it (read). The
only `-C` in the client is the canary's `movesCwd`, which refuses a pinned `sq` command line
that moves the working directory (`test/canary/resolveSq.ts`, read). A pin of `sq -C <dir>` is
refused there, which is correct under this decision.

**What already exists to build on.** `resolve()` takes a `client_cwd`, the resolution base for
the walk-up, documented as "the requesting client's working directory, not necessarily this
process's", with a future server handler named as a caller (read). The root callback captures
`Path.cwd()` into `RequestContext.client_cwd`, and every resolution site reads it from there:
the gate (`apply_gate`), the version notice, `bind_active_spec`, `open_service`, and the
`_role`, `_workflow_cmd` and `_main` call sites (read, by grep of `client_cwd`).

## Decision

### 1. Meaning of `-C`

- `-C <path>` is an option of the root command only. `sq -C <path> <command> ...` behaves as
  `cd <path> && sq <command> ...` would, in every respect this decision lists below.
- **Relative to what.** A relative `<path>` is taken against the process working directory.
- **Repeatable, as in git.** Each `-C` after the first, when not absolute, is taken against the
  one before it; an absolute one replaces everything before it. An empty value leaves the
  directory unchanged. The effective directory is the process working directory joined with
  every value in order, then resolved physically (symbolic links resolved before `..`, as
  `chdir` does). `Path.joinpath` with an empty component and with an absolute component behaves
  exactly this way (driven, scratch probe).
- **Position.** `-C` must come before the command, as in git. It is not added to the hoisted
  global options: a hoisted short option would also capture a `-C` that is the value of another
  option, such as `-m -C`, the token shape REV-995 F21 found for `--help`, and the client never
  places it anywhere else. `sq list -C x` is Click's own "no such option" refusal from `list`.
- **No long form.** git has none, and the operator's ruling names `-C`.
- **Relative path arguments follow `-C`.** "As if started in `<path>`" covers every relative
  path the command reads: `--file` bodies and comments (`_common._read_source_file`), the
  `sq import` event file (`_import.py`), and the root `init` and `adopt` create (section 2).
  `-` (stdin) is unaffected. A path argument resolved against the process directory while the
  squad is resolved against `-C` would be a second meaning of "here" in one command.

### 2. Mechanism: threaded, never `chdir`

- The effective directory is computed once by one helper from the root group's parsed `-C`
  values and the process working directory, and becomes `RequestContext.client_cwd`. Every
  site in the list above already reads `client_cwd`, so squad resolution changes in one place.
- `os.chdir` is rejected: it is process-global state, which ADR-534 rules out, it would leak
  between in-process `CliRunner` invocations in the suite, and it is unsound for the server
  handler `client_cwd` was introduced for.
- **Before the root callback.** Click resolves a subcommand name before it invokes the group
  callback, so the two pre-callback spec lookups (`resolve_spec_for_ctx` and
  `_pending_spec_error`, which today read `ctx.params["dir"]`) call the same helper on
  `ctx.params`. They must not read the bound context's `client_cwd` there: at that point it is
  the previous invocation's (read). The root option's own callback runs while the root group's
  parameters are parsed, before `get_command` is called, and the parsed `-C` values are already
  in `ctx.params` inside `get_command` (driven, scratch Typer probe with a `TyperGroup`
  subclass). ADR-263's lazy custom-type lookup therefore keeps working unchanged in shape.
- **Errors.** The option's callback refuses, with exit 2 like an invalid `--at`, a `-C` whose
  effective directory does not exist or is not a directory, naming the resolved path. Because
  it runs during parsing, the refusal comes before any command or custom-type lookup (driven,
  same probe: `-C /nonexistent widget` exits 2 on the `-C` message, not on "no such command").
  A directory in no squad is what it is from that directory today: `NotInitializedError`, whose
  message names the effective directory whenever `-C` was given.
- **`init` and `adopt`.** Both create at the effective directory: the root passed to the
  service is `client_cwd`, and the `[init.names]` read in `_cli/_main.py` uses the same root.
  `sq -C X init` creates `X/.squads.toml` and `X/squads/`, and `--squad-dir` names the folder
  inside `X`, exactly as `cd X && sq init`. `X` must exist; `-C` never creates a directory, as
  in git. This closes BUG-1008: the flag is no longer ignored. Its stated expectation (the
  squad created *at* X) becomes "the project created at X", which is the `-C` meaning.

### 3. `--dir` is refused, not aliased

`--dir` is removed from the root command and replaced by a hidden option whose callback refuses
with exit 2: `--dir is no longer supported; use -C <path> to run sq as if started in <path> (the
project directory, or any folder inside it)`. It stays in the hoisted options so the refusal is
the same wherever it is written. This follows ADR-1007, which refuses a renamed override key
with no alias. An alias was weighed and rejected under Alternatives. The refusal is kept
through the 0.x line and removed with the 1.0 contract.

### 4. The backwards inference goes away

Removed from `_paths.py`: the `dir_override` parameter of `resolve()`, the config-names-folder
check and its refusal, `_holds_squad_data` and its refusal, and the synthesised default
configuration. `resolve()` is the walk-up from `client_cwd` and nothing else, with
`client_cwd` defaulting to `Path.cwd()` for non-CLI callers. `open_service` loses
`dir_override`; `RequestContext.active_dir` and `_common.set_active_dir` go. The F26 refusal
TASK-954 lands is therefore temporary by design: it keeps 0.16 free of the bypass until this
lands, and is deleted with the rest. Its CHANGELOG entry and the two docs/faq.md entries for its
refusals are replaced, not amended, since neither was released.

### 5. Gate guarantee

The schema gate sees exactly the configuration it would see when run from the effective
directory, because there is one resolver and one base: `apply_gate` resolves through
`resolve(client_cwd=...)`, the same call as every command. No synthesised configuration exists
any more, so no layout can produce a configuration stamped at the package's schema for a
folder whose squad is behind (inferred from the code once section 4 lands; to be proven by the
tests below).

What proves it, beyond rows:

- **A differential test over the layout family.** For each REV-995 layout (project root with
  `"."` and `"./"`, nested, renamed, two-level, outside the tree with `"../shared"` and an
  absolute path, a nested project under another squad, symlinked folders) and each gate
  direction, `sq -C <folder> <command>` from elsewhere must equal `cd <folder> && sq
  <command>` in exit code, stdout, stderr and the digest of every file under the project.
  The equality is the property; the rows in the gate table become its instances.
- `-C` at the squad folder, at the project root and at a subfolder of the squad each gate a
  behind squad.
- A guard (in `tests/meta`) that no squad-resolution call site reads `Path.cwd()`: the only
  read is at the CLI edge, where the effective directory is computed.
- Falsify each: point the gate's `resolve` at the process directory and watch the
  differential test go red for every `-C` row.

### 6. Docs, help text and other prose

Root help for `-C`: `Run as if sq was started in PATH (repeatable; relative to the previous
-C).`, metavar `PATH`. The 16 `--dir` mentions in adopter and contributor docs change (read,
grep excluding `--direction`): README.md:168 and :287; docs/README.md:68; docs/faq.md:9, the
two refusal entries at :12-19 (replaced by entries for the `-C` and `--dir` refusals), :99;
docs/migration.md:63, plus a 0.16 upgrade note on the break; docs/internals.md:49, :62, :64,
:380, :396; docs/overrides.md:2106. CHANGELOG: the unreleased `--dir` gate entry is replaced
by a breaking-change entry for `-C`; released entries stay. Outside the docs: CLAUDE.md:37 and
:102 (outside the managed region), GUIDE-79's CLI paragraph, the VS Code client's
`squadDir.ts` doc comment, the `_errors.py` and `_index/_store.py` comments that name
`--dir`, and the board notice on scratch squads that says "addressed with `--dir`". Six test
files carry 16 `--dir` uses (read): the gate table, the hoist unit tests, and four others. No
bundled template mentions `--dir` (read), so no bundled file needs to change.

### 7. ADRs that need a dated note

- **ADR-263**: its accepted option reads `--dir` from the Click context inside `get_command`;
  the note says it reads the `-C` values through the shared helper, and that Option 2's
  `--dir` pre-scan discussion is historical.
- **ADR-622**: "`--dir` — the usual squad selector" becomes `-C`.
- **ADR-534**: lists the resolved squad folder as a former global that became a context field;
  the note says `active_dir` is removed and `client_cwd` carries the effective directory.
- ADR-249, ADR-266 and ADR-153 name "the root `--dir` callback" only as a label for the root
  callback. Its role is unchanged, so no note is needed.

### 8. Build order

This changes no bundled file and no schema, so the bump does not gate it. It must follow
TASK-954, whose F26 refusal it deletes, and it touches `_paths.py`, `_cli/__init__.py`,
`_cli/_common.py`, `_context.py`, `_services/_service.py`, `init` and `adopt` in
`_cli/_main.py`, and the gate table, which FEAT-980 and the ADR-1007 flattening do not
(inferred from their scope). It goes in the main stream right after TASK-954: TASK-954, this
decision, FEAT-980, the bump, the ADR-1007 flattening, TASK-989, TASK-990, FEAT-976, FEAT-977,
then FEAT-961 and FEAT-966. If the stream is busy, it can run in its own worktree beside
FEAT-980 and merge before the bump. It has no feature or task yet.

## Consequences

- One resolver: a squad is found the same way whether `sq` is run in a folder or pointed at
  it, so a gate bypass needs a defect in ordinary use, not a second code path.
- Breaking for scripts that pass `--dir`, refused with the replacement named. For an in-tree
  squad, `-C <squad folder>` works unchanged in meaning, because the walk up from the squad
  folder reaches its configuration; a squad kept outside its project tree is reached with
  `-C <project>`.
- `-C` into a folder with no configuration of its own resolves the enclosing squad, as `cd`
  would. An agent probing a scratch squad that sits inside a real project tree reaches the
  real squad; scratch squads belong outside any project tree (this repository's scratchpad is
  under `/tmp`).
- A mistyped `-C` is refused instead of running on a synthesised squad.
- `sq init` and `sq adopt` honour the flag.

## Alternatives

- **Keep `--dir` and fix the inference again.** Rejected by the operator's ruling, and by the
  record: four review passes, each closing the shapes it was shown.
- **Alias `--dir` to `-C`.** It would give the right squad for most in-tree layouts, but
  silently changes meaning where it does not: a folder outside its project tree, and a folder
  that is not a squad, which today gets a synthesised squad and would then resolve an enclosing
  one. Rejected, following ADR-1007.
- **Remove `--dir` with no refusal.** Click's "no such option" names neither `-C` nor why.
- **`-C` names the project root, with no walk-up.** Considered and rejected, per the
  operator's correction of 2026-10-15T19:16:53Z on MILE-934. It would still be a resolver
  beside the walk-up, with its own refusal for a folder below the root, so `-C <folder>` and
  `cd <folder> && sq` would answer differently for the same folder, the difference this
  decision exists to remove.
- **`os.chdir` at the CLI edge.** Rejected in section 2.
- **Hoist `-C` from any position.** Rejected in section 1.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-15T19:17:34Z] `architect` Robert Architect:
  - 2026-10-15: drafted from the op-pierre rulings on MILE-934 (2026-10-15T19:11:19Z, corrected at 19:16:53Z: -C keeps the walk-up). The no-walk-up reading is listed only under Alternatives, as rejected.
  - @manager for the operator: (1) -C is repeatable as in git and must come before the command (not hoisted). (2) Relative path arguments (--file, the sq import file) resolve against -C, which is what "as if started in" means. (3) --dir is refused with a message naming -C (exit 2) through the 0.x line, not aliased; an alias would work for most in-tree layouts, so that is the operator call to confirm. (4) sq -C X init needs X to exist and creates X/.squads.toml + X/squads; BUG-1008 asked for the squad AT X, so its expectation changes.
  - @manager build order: right after TASK-954, before FEAT-980; no bundled file or schema change, so the bump does not gate it. It has no feature or task yet. The board notice on scratch squads (addressed with --dir) and the private memory on scratch cd failures both name --dir and need rewording once it lands. Dated notes owed on ADR-263, ADR-622 and ADR-534 once accepted.
- [2026-10-15T19:19:36Z] `op-pierre` Pierre Chat:
  - 2026-10-15, on the four points of this record, all confirmed:
    
    1. `--dir` is refused with a message naming `-C`, with no alias.
    2. `-C` comes before the command and can be repeated, git-style.
    3. Relative path arguments resolve against `-C`.
    4. `sq -C X init` creates `X/.squads.toml` with the squad in `X/squads`.
- [2026-10-15T20:11:53Z] `op-pierre` Pierre Chat:
  - 2026-10-15: accepted.
- [2026-10-15T20:17:28Z] `architect` Robert Architect:
  - @manager Dated notes are added for all three ADRs in section 7, each as "Note 2026-10-15 (ADR-1009)" at the affected passage, and each has a related ref back to this record: ADR-263 (after the Recommendation; get_command reads the parsed -C values through the shared helper, and the --dir discussion in Options 1 and 2 is historical), ADR-622 (the CLI surface's --dir bullet becomes -C before the command), ADR-534 (after the section 1 inventory; active_dir and set_active_dir are removed, and client_cwd carries the effective directory).
    None was skipped. ADR-249, ADR-266 and ADR-153 got nothing, as section 7 says.
    Every diff against HEAD is additions only, apart from the updated_at the body verb stamps. No status changed, no stray content tags, and sq check is clean.
<!-- sq:discussion:end -->
