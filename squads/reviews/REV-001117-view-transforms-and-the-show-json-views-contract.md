---
id: REV-1117
sequence_id: 1117
type: review
title: View transforms and the show --json views contract
status: Approved
author: reviewer
refs:
- TASK-1110
description: Review of TASK-1110 ST1-ST7 (commit 12c1888f) against ADR-1109.
subentities:
- local_id: F1
  title: 'A transform can mutate the active spec: only source and item are copied'
  status: Verified
  severity: medium
- local_id: F2
  title: A NUL character in an override transform path raises a traceback in show,
    check and lint
  status: Verified
  severity: low
- local_id: F3
  title: The JSON walk accepts an int too large to serialize; show --json then raises
    a traceback
  status: Verified
  severity: low
- local_id: F4
  title: SystemExit from a transform makes sq check and show --json exit 0 with no
    output
  status: Verified
  severity: low
- local_id: F5
  title: read_body docstring still lists the show --json body field as one of its
    surfaces
  status: Verified
  severity: low
- local_id: F6
  title: 'Call-time lookups of the transform module fail once it leaves sys.modules:
    document it'
  status: Verified
  severity: info
- local_id: F7
  title: 'Test economy: an unfailable sort claim, duplicated shape rows, a decorative
    decoy'
  status: Verified
  severity: info
created_at: '2026-10-24T14:14:37Z'
updated_at: '2026-10-25T19:39:36Z'
---
<!-- sq:body -->
## Scope

Commit 12c1888f on `release/0.17`: TASK-1110 ST1 to ST7 for FEAT-1108, against ADR-1109 and the five points the operator accepted on it. Covered: `src/squads/_transform.py`, `src/squads/_view_transforms.py`, the declaration and override checks in `_workflow/_models.py` and `_workflow/_loader.py`, `resolve_within` in `_paths.py`, tag expansion and `view_data` in `_views.py`, `read_stored_body`/`view_data` in `_services/_items.py`, the `show --json` builders (`_cli/_common.py`, `_cli/_skill.py`, the `self` kind of `sq workflow view --json`), `sq workflow views --json`, the `view_transform_resolves` check, the rewritten `milestone_rollup` template, the scaffold text, and the new and changed tests. ST8 and ST9 (docs, CHANGELOG) are out of scope.

## Method

- Drove the dev build (`uv run --all-extras sq`) in five scratch squads: root, subdirectory and `-C` resolution with a decoy squad as the process cwd; an override `path` on `milestone_rollup`; a `self`-kind probe view with its own transform and template; disabled tags; directory, symlink-loop, intermediate-directory-symlink, NUL-byte and over-long paths; raising, exiting, mutating and oversized-output transforms on `show`, `--raw`, `show --json`, `sq workflow view` (text and `--json`), `sq check` and `sq workflow lint`.
- In-process probes through `open_service(client_cwd=...)` and `TransformLoader` for spec mutation and for idioms that need the module registered at call time.
- Read every changed source line; checked the import-edge table, the mutable-state guard, comments, aliases and error classes.
- Targeted tests only: `tests/meta` plus the new and changed view tests, 548 passed. No full suite.

## Verdict summary

The core holds. The squad directory comes from `-C` and the client cwd, never the process cwd, in the CLI and through `open_service(client_cwd=...)`, a second squad in one process included. Confinement runs before any user code executes: an outward symlink at the file or at an intermediate directory is refused on every surface, and the sentinel never fires. Nothing stays in `sys.modules`, no bytecode cache is written under `.overrides/`, an edited file is read again, and copies of `source` and `item` keep a mutating transform away from disk. `show --json` returns the stored body with its tags on item, skill and `self` surfaces, and `views` follows the enabled, resolvable, transform-only rule.

The four deviations in the developer's handback are accepted. The always-on `view_transform_resolves` check is where `sq check` should report this. Compiling the file from its bytes fixes the stale-edit case and also keeps `__pycache__` out of `.overrides/`. The local `_paths` import is justified: a top-level import would pull `_transform` into the `_paths`/`_workflow`/`_views` cycle. The scaffold needing its file to lint clean follows from the always-on check.

Findings: the read-only guarantee does not cover `spec` (F1). Three inputs turn into tracebacks or a silent exit 0 instead of a clean error (F2 to F4). One docstring went stale (F5). One loader consequence should be documented (F6). Test-economy notes are in F7. Recommended verdict: ChangesRequested on F1 to F5, which are small. F1 and F4 need an architect ruling first.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1117 add-finding "…" --severity medium`; track with `sq review 1117 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — A transform can mutate the active spec: only source and item are copied

<!-- sq:finding:F1:body -->
**Label:** driven (in-process, within one request); inferred (across daemon requests, from ADR-1052 clause 10).

ADR-1109 says reads are read-only, enforced by copying. It deep-copies `source` and `item` and passes `spec` as is, because "spec is frozen". `WorkflowSpec` is `frozen=True`, but frozen only blocks attribute assignment. Its containers (`items`, `views`, `statuses`, ...) are ordinary `dict`s, and a transform can change them. `src/squads/_transform.py:88-89` passes the live object.

Reproduction (`open_service(client_cwd=<squad>)`, with an override transform `def f(source, *, spec): spec.items.pop('bug', None); spec.views.pop('memory_skill', None); return {'ok': True}`):

```
before: True True
{'milestone_rollup': {'ok': True}}
after: False False
```

The rest of the same request (badges, sub-entity kind lookups and any later tag) sees the mutated spec. ADR-1052 clause 10 keeps the parsed spec warm across daemon requests while its source files are unchanged. So this is the cross-request leak ADR-1109 lists as the reason for copying, reached through the one argument it does not copy.

Needs an architect ruling: copy `spec` too, pass a read-only view, or narrow the read-only claim to `source` and `item` and document it. @architect
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-24T14:17:43Z] `architect` Robert Architect:
  - Ruling: deep-copy `spec` per call, like `source` and `item` (`model_copy(deep=True)`, measured about 0.4 ms on the bundled spec). A read-only proxy is rejected as more machinery for no gain. ADR-1109 Call section amended. @tech-lead
- [2026-10-24T14:21:27Z] `python-dev` Elias Python:
  - spec is now passed as a deep copy per call (_transform.py); the copy test mutates spec.items and asserts the bundled spec is intact.
- [2026-10-24T14:29:16Z] `reviewer` Paul Reviewer:
  - Verified on af38f60a (driven): spec.items.pop and a nested source.__dict__ write inside a transform leave svc.spec unchanged after view_data.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — A NUL character in an override transform path raises a traceback in show, check and lint

<!-- sq:finding:F2:body -->
**Label:** driven.

The load-time shape check (`_transform_path_problems`, `src/squads/_workflow/_models.py:2554`) accepts a NUL character in `path`. TOML allows `"t\u0000x.py"`. `resolve_within` (`src/squads/_paths.py:54-55`) then raises `ValueError: lstat: embedded null character in path`. Nothing on the render or check path catches that, so a traceback comes out instead of a `ViewTransformError`:

```
[views.milestone_rollup]
transform = { path = "t\u0000x.py", function = "f" }
```

`sq milestone 14 show --json`, `sq check` and `sq workflow lint` all print a Rich traceback ending in that ValueError, from `_transform.py:131` via `resolve_within`. `sq workflow lint` is the command meant to explain a broken override.

Fix: refuse a control character in `path` in the shape check, or turn `ValueError`/`OSError` from `resolve_within` into the view error. The first keeps it a load-time lint finding.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-24T14:21:29Z] `python-dev` Elias Python:
  - A control character in a transform path is refused by the load-time shape check (a lint finding), with a row in the shape table.
- [2026-10-24T14:29:18Z] `reviewer` Paul Reviewer:
  - Verified (driven): \u0000, \u0001, \u001f and a newline in path are refused at load with "control characters" on show, check and lint, no traceback; DEL (\u007f) passes the check and gives a clean "is not a file".
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — The JSON walk accepts an int too large to serialize; show --json then raises a traceback

<!-- sq:finding:F3:body -->
**Label:** driven.

The JSON walk (`_json_problem`, `src/squads/_transform.py:253`) accepts any `int`. An int beyond Python's integer-to-string limit (4300 digits) passes the walk, then fails when it is serialized. `def f(source): return {"big": 10**5000}` makes `sq milestone 14 show --json` exit 1 with a Rich traceback ending in `ValueError: Exceeds the limit (4300 digits) for integer string conversion`, not a clean error naming `$.big`. ADR-1109 has the walk decide what is JSON data, so that the template and JSON receive the same value. This value passes the walk and reaches neither cleanly.

Fix: in the walk, refuse an `int` whose `str()` raises, naming its JSON path. Low because only a pathological transform hits it, but it is the one walk input that escapes as a traceback.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-24T14:21:31Z] `python-dev` Elias Python:
  - The JSON walk refuses an int that cannot be serialized, naming its JSON path; row added to the bad-return table.
- [2026-10-24T14:29:20Z] `reviewer` Paul Reviewer:
  - Verified (driven): 10**5000 and -(10**5000) give a clean error naming $.big; 10**4299 nested in a list next to True still passes.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — SystemExit from a transform makes sq check and show --json exit 0 with no output

<!-- sq:finding:F4:body -->
**Label:** driven.

ADR-1109 catches only `Exception`, so `KeyboardInterrupt` and `SystemExit` propagate (`src/squads/_transform.py:92`, `:186`). For `KeyboardInterrupt` that is right. For `SystemExit` the result is a quiet wrong answer on the gate:

- A transform file with `import sys; sys.exit(0)` at top level: `sq check` prints nothing and exits **0**. The gate reads clean although the always-on `view_transform_resolves` check never finished, and nothing else in the check ran to completion either.
- `def f(source): raise SystemExit(0)`: `sq milestone 14 show --json` exits **0** with empty stdout, so a JSON client gets a parse failure from a success exit.

The design rules propagation, and this is the consequence on the check surface. Asking the architect whether `SystemExit` raised by user code (at import or call) should become a `ViewTransformError` like any other failure, with only `KeyboardInterrupt` propagating. @architect
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-24T14:17:44Z] `architect` Robert Architect:
  - Ruling: `Exception` and `SystemExit` from a transform (import or call) become `ViewTransformError`; every other `BaseException` propagates, so `KeyboardInterrupt` interrupts and `asyncio.CancelledError` cancels. Catch `(Exception, SystemExit)` explicitly, not `BaseException`. ADR-1109 Errors section amended. @tech-lead
- [2026-10-24T14:21:33Z] `python-dev` Elias Python:
  - (Exception, SystemExit) is caught at import and call and becomes ViewTransformError; other BaseExceptions propagate. Two rows (call, import) added.
- [2026-10-24T14:29:22Z] `reviewer` Paul Reviewer:
  - Verified (driven): SystemExit(0), ("bye"), (None) and sys.exit(3) at call give a view error, exit 1; sys.exit(0) at import makes sq check report "import failed" (exit 3) and lint exit 1; KeyboardInterrupt still exits 130. GeneratorExit propagates as a traceback, which the amended ruling covers.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — read_body docstring still lists the show --json body field as one of its surfaces

<!-- sq:finding:F5:body -->
**Label:** read.

`ItemsMixin.read_body`'s docstring (`src/squads/_services/_items.py:743-747`) still lists "the `--json` body field" among the surfaces that read through it, and says nothing else reads the `sq:body` region for display. `build_item_json` and the skill `show --json` builder now read `read_stored_body`. Drop the `--json` surface from the list and point to `read_stored_body` for the stored text.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-24T14:21:35Z] `python-dev` Elias Python:
  - read_body docstring no longer lists the --json body field and points to read_stored_body.
- [2026-10-24T14:29:25Z] `reviewer` Paul Reviewer:
  - Verified (read): the read_body docstring now covers text surfaces only and points show --json to read_stored_body.
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Call-time lookups of the transform module fail once it leaves sys.modules: document it

<!-- sq:finding:F6:body -->
**Label:** driven.

ADR-1109 keeps an override module in `sys.modules` only while it executes. Anything that looks the module up by name at call time therefore fails, unlike the same code in an ordinary module. Driven through `TransformLoader` with one file:

- `typing.get_type_hints(Row)` on a dataclass with a forward-reference annotation: `NameError: name 'Later' is not defined`
- a pydantic model with a forward reference to a later class: `PydanticUserError: M is not fully defined`
- `pickle.dumps` of a dataclass instance: `PicklingError: No module named '_squads_view_transform_...'`

Each comes out as a clean `ViewTransformError` with the line, so nothing breaks badly. An adopter will still meet it with no idea why. Not a code defect within the ruling: ST8 (@tech-writer) should state the constraint in the transform docs. If the architect prefers, the loader could keep the module registered for the loader's lifetime (one read) without changing what ADR-1109 guarantees across reads.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-24T14:38:30Z] `tech-writer` Theo Writer:
  - Documented in docs/overrides.md section "Giving a view a transform" (paragraph "The file is not a registered module when the function runs": get_type_hints with a forward ref, a pydantic forward ref and pickle each named with the error the dev build gives), and in the 0.17.0 CHANGELOG Added entry for view transforms. Driven in a scratch squad: all three fail as stated; plain dataclasses work.
- [2026-10-25T19:39:36Z] `reviewer` Paul Reviewer:
  - Holds: docs/overrides.md "The file is not a registered module when the function runs" and the 0.17 CHANGELOG transform entry state the constraint.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Test economy: an unfailable sort claim, duplicated shape rows, a decorative decoy

<!-- sq:finding:F7:body -->
**Label:** read; the reddening claims checked against the developer's falsification notes.

The operator asked for a test-economy pass. No test is missing for a real gap. Four tests overclaim or duplicate:

1. `tests/service/test_view_transforms_through_the_service.py::test_the_rollup_partitions_on_status_roles_and_sorts_by_type_then_sequence`: no row puts two members in one partition, so the sort in its name cannot fail. The `assignee` column is always `None`. The sort is really covered by `tests/service/test_milestone_rollup_section_order.py`, which now feeds the transform's output to the template. Rename it to the partition claim and drop the unused `assignee` column.
2. `_REFUSED_OVERRIDES` rows 4 and 5 (`..`, `function = "class"`) repeat rows of `tests/unit/test_view_transform_engine.py::test_a_transform_declaration_is_checked_for_shape_alone` through the same `view_transform_problems`. Only rows 1 to 3 test the override pre-merge check. Drop rows 4 and 5.
3. `tests/cli/test_view_transforms_cli.py::test_dash_c_finds_the_transform_of_the_named_squad_not_the_working_directory`: the decoy is `<decoy>/transforms/t.py` in a folder that is not a squad, a place no process-cwd bug would read. The test still reddens under such a bug (as "not a file"), so it stays. The decoy file only decorates, and the service test already uses a real decoy squad. Drop the decoy file, or make the decoy a squad.
4. `tests/cli/test_view_transforms_cli.py::test_lint_and_check_refuse_a_transform_that_escapes_the_overrides_folder` asserts `"outside" in checked.output`, and the target file is named `outside_transform.py`. Any message that names the target passes. Assert `"outside .overrides/"`, the phrase the unit test already pins.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-24T14:21:38Z] `python-dev` Elias Python:
  - Rollup test renamed to the partition claim and assignee dropped; two duplicate refusal rows removed; -C decoy now sits at <cwd>/.overrides where a cwd bug would read it; check assertion pins 'outside .overrides/'.
- [2026-10-24T14:29:27Z] `reviewer` Paul Reviewer:
  - Verified (read): the rollup test is renamed with the assignee column gone, the duplicate shape rows are dropped, the decoy sits under .overrides/, and the check assertion pins "outside .overrides/". 64 passed across the three view-transform test files.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-24T14:15:55Z] `reviewer` Paul Reviewer:
  - Filed 7 findings on commit 12c1888f (TASK-1110 ST1-ST7). Recommended verdict: ChangesRequested on F1-F5; F6 and F7 are info.
  - @architect a ruling is needed on F1 (spec is mutable through its dicts; ADR-1052 keeps it warm across daemon requests) and F4 (SystemExit from user code exits 0 on sq check).
  - @python-dev F2, F3, F5 and F7 are small; F1 and F4 wait for the ruling. @tech-writer F6 belongs in ST8.
- [2026-10-24T14:29:36Z] `reviewer` Paul Reviewer:
  - Approved: F1-F5 and F7 Verified against the original reproductions and variants. F6 stays Open (info) for the tech-writer in TASK-1110 ST8; an info finding does not block approval.
  - @architect ADR-1109 was amended (c7610392) but its own discussion has no comment recording the change; the rulings sit on REV-1117 F1/F4 only. Under the ADR-amendment rule, add a dated comment on ADR-1109.
<!-- sq:discussion:end -->
