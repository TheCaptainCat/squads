---
id: REV-1223
sequence_id: 1223
type: review
title: Review of the daemon feature's delivered tasks
status: ChangesRequested
author: reviewer
refs:
- FEAT-1140
- TASK-1217
- TASK-1218
- TASK-1263
- TASK-1262
subentities:
- local_id: F1
  title: role add/update --file bypass attachments and read the serving process's
    cwd
  status: Verified
  severity: high
- local_id: F2
  title: Seeded terminal facts force_terminal and override the client's FORCE_COLOR/TTY_COMPATIBLE
  status: Verified
  severity: medium
- local_id: F3
  title: Typer's help and usage-error consoles ignore seeded terminal facts
  status: Noted
  severity: medium
- local_id: F4
  title: No test covers terminal facts reaching the consoles; build_consoles(None)
    mutation survives
  status: Noted
  severity: medium
- local_id: F5
  title: Override remedy path still spelled from the process directory in a served
    request
  status: Verified
  severity: low
- local_id: F6
  title: Prompt after a committed transaction does not fail as ADR-1052 point 12 states
  status: Noted
  severity: low
- local_id: F7
  title: Attachments decoded outside the CLI; invalid UTF-8 --file escapes as a traceback
  status: Verified
  severity: low
- local_id: F8
  title: Comment-removal listing before NeedsTerminal; vacuous --version stderr row
  status: Verified
  severity: info
- local_id: F9
  title: 'Local-mode changes from the fix have no CHANGELOG entry: role --file under
    -C, clean non-UTF-8 refusal'
  status: Verified
  severity: low
- local_id: F10
  title: 'test_in_process_entry.py breaks ADR-1172 rules 3-5: direct run()/unit calls,
    file reads, no covers'
  status: Verified
  severity: medium
- local_id: F11
  title: A role definition file that is not UTF-8 is reported as a role override
  status: Verified
  severity: low
- local_id: F12
  title: 'role --file read errors still mix wordings: a missing file says role override,
    an unattached one says file'
  status: Verified
  severity: low
- local_id: F13
  title: Retirement and vocabulary checks run before a request queues, not before
    it runs
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F14
  title: Single-item reads of sub-entity lists, refs and roster entries answer no
    ETag
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F15
  title: skills link-role and unlink-role ignore If-Match
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F16
  title: GET-no-mutate case samples 12 of 53 GETs; two cases assert part of the response
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F17
  title: Stream guard misses indirect writers; the daemon logger writes a 500 to stderr
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F18
  title: Lane A wire decisions to record in ADR-1225
  status: Verified
  assignee: architect
  severity: info
- local_id: F19
  title: 'SIGTERM kills the daemon before its cleanup: all four runtime files stay'
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F20
  title: daemon status and stop report none running when the identity call fails,
    while the lock is held
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F21
  title: Unbounded idle_timeout_minutes overflows the idle deadline; GET /v1/daemon
    answers 500
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F22
  title: Socket Content-Type/Squads-Client rule is untested and beyond ADR-1052; HEAD
    refused as a write
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F23
  title: Endpoint resolution unit tests and a substring migrate assertion break ADR-1172
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F24
  title: The .squads.toml walk-up is duplicated in _paths and _endpoint despite the
    one-place rule
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F25
  title: Reserving daemon breaks an adopter type or alias of that name; no migration
    note says so
  status: Verified
  assignee: tech-writer
  severity: low
- local_id: F26
  title: Lock released before its file is unlinked lets two daemons hold one key
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F27
  title: Admission types misdirected/forbidden are absent from the error table and
    the OpenAPI document
  status: Verified
  assignee: architect
  severity: info
- local_id: F28
  title: daemon_config_valid reads the serving process's SQUADS_DAEMON in remote mode
  status: Verified
  assignee: python-dev
  severity: info
- local_id: F29
  title: 'Windows and macOS paths unrun: CLI port admission, SO_EXCLUSIVEADDRUSE,
    runtime-dir ACL'
  status: Verified
  assignee: python-dev
  severity: info
- local_id: F30
  title: One Ctrl-C does not end HttpApi's wait under asyncio.run
  status: Verified
  assignee: python-dev
  severity: high
- local_id: F31
  title: Parity run misses a dropped Client-Dir or Session-Id header
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F32
  title: Hosted-squad retry and Client-Dir omission are not built
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F33
  title: Remote refusal tests cannot see a fall back; pin v0.19
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F34
  title: Vocabulary guard parses only --help; self-check tests CPython
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F35
  title: OpenAPI document omits 403 on GETs, the daemon routes' refusals and 405
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F36
  title: A repeated single-value query key silently keeps its last value
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F37
  title: An unusable daemon setting falls back to local mode with nothing on stderr
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F38
  title: An unreachable daemon runs the call locally with no restart or line; the
    TUI never reselects
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F39
  title: A session restarts a daemon from its first endpoint, ignoring enabled = false
    set since
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F40
  title: 'A session retries a failed daemon start on every call: one line and up to
    6 s each'
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F41
  title: Switched-off session test leaks a daemon when it fails
  status: Fixed
  assignee: python-dev
  severity: low
- local_id: F42
  title: Frontmatter cached under two spellings of each item path; the sweep grace
    walk exists to keep the copy
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F43
  title: RequestScope._context binds a partial ambient context so the override check
    can reach the cache
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F44
  title: Frontmatter cache is consulted inside transaction(), against ADR-1261 point
    7's wording
  status: Verified
  assignee: architect
  severity: info
- local_id: F45
  title: ParseCache.item_files() serves only an internal-reading test; digest() duplicates
    digest_of()
  status: Fixed
  assignee: python-dev
  severity: low
- local_id: F46
  title: 'The copy-per-hit rule is unguarded: sharing cached objects keeps the remote
    suite green'
  status: Verified
  assignee: python-dev
  severity: info
- local_id: F47
  title: Click's cached stream wrapper fixes the first client's encoding for every
    later served command
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F48
  title: A daemon started under SQUADS_SPANS still prints spans into every served
    command's stderr
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F49
  title: Terminal facts (tty, size, windows_vt) and the end-of-input answer are untested;
    dropping them stays green
  status: Verified
  assignee: python-dev
  severity: medium
- local_id: F50
  title: Served Typer help ignores PY_COLORS, GITHUB_ACTIONS, TERMINAL_WIDTH; private
    console patch sits outside install()
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F51
  title: 'Windows: Rich picks the served colour system from the daemon''s console,
    not the client''s'
  status: Fixed
  assignee: python-dev
  severity: low
- local_id: F52
  title: The no-self-call guard misses HttpApi, urllib, os spawn calls and any fourth
    endpoint module
  status: Fixed
  assignee: python-dev
  severity: low
- local_id: F53
  title: The endpoint parity harness builds a command tree per test, not once per
    session as ADR-1261 point 9 says
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F54
  title: select_api refusal tested as an internal unit; endpoint file grew past the
    planned rows
  status: Verified
  assignee: python-dev
  severity: low
- local_id: F55
  title: client_dir is validated and ignored, where ADR-1261 point 2 says it is bound
    as the effective directory
  status: Verified
  assignee: architect
  severity: info
- local_id: F56
  title: ADR-1261 says the Typer console replacement is restored; nothing restores
    it
  status: Fixed
  assignee: architect
  severity: info
created_at: '2026-10-28T18:45:17Z'
updated_at: '2026-10-30T22:39:29Z'
---
<!-- sq:body -->
Batch review of FEAT-1140's delivered tasks, one commit at a time, against ADR-1052 and each task's acceptance.

## Scope

- TASK-1217, commit 22ce7f65: the in-process command entry (`run`), per-invocation consoles, the request-seeded `RequestContext` (start directory, attachments, terminal facts, documents), attachment-served file reads, and the prompt helper that signals `NeedsTerminal`.
- TASK-1263, commits ff9784bf and 4585afec: the daemon's content-keyed cache of the index, item frontmatter and the override check (ADR-1261 point 7).
- TASK-1262, commits fc95085f, fb353e94 and c6631735: the private command endpoint `POST /v1/commands`, served execution on the daemon's own `LocalApi`, the stdio and `os.environ` proxies, attachments and stdin, two-phase prompts, and the endpoint and route parity modes (ADR-1261 points 1, 2, 3, 5 and 9).
- Later tasks of FEAT-1140 join this review as they land.

## Method

- Local-mode parity: the parent commit's CLI and this commit's CLI run side by side on one scratch squad, under a pseudo-terminal and piped, across colour and width environments, compared byte for byte.
- The seeded path: probes through `run(argv, seed=...)` for isolation sequences, attachments, terminal facts and prompts.
- Tests: a sample of the new rows falsified against deliberate breakage.
<!-- sq:body:end -->

## Findings

_Severity:_ 🔴 critical · 🟠 high · 🟡 medium · 🟢 low · 🔵 info

_Add with `sq review 1223 add-finding "…" --severity medium`; track with `sq review 1223 finding <n> update --status <Status>`._

<!-- sq:findings -->

<!-- sq:finding:F1 -->
### F1 — role add/update --file bypass attachments and read the serving process's cwd

<!-- sq:finding:F1:body -->
`sq role add --file` and `sq role <slug> update --file` read their file with `read_role_toml(file)` (`_roles/_resolver.py` → `read_override_text`), a plain `Path` read. They never go through `read_client_text`, so in a served request (attachments seeded):

- an unattached file is **read from the serving process's own filesystem, relative to its own working directory**, instead of being refused;
- an attached file is not found (`Cannot read role override r2.toml: [Errno 2] …`).

This breaks US1 ("a file the command names is read from the attachments; an unattached path is refused") and ADR-1052 point 9 ("every `--file` option"). The task body listed only `_read_source_file` and the import read, but the acceptance is general and these two options use the same `common.file_option` helper.

Repro (dev tree, scratch squad `sq1`, process cwd `elsewhere/` holding `r.toml`):

```python
os.chdir(elsewhere)  # contains r.toml: full_name = "Daemon Disk" ...
run(["role", "add", "probe-role", "--file", "r.toml", "--as", "manager"],
    seed=RequestContext(start_dir=squad, attachments={}))
# -> role "Daemon Disk" created from the process cwd's r.toml; no refusal
run(["role", "add", "probe-two", "--file", "r2.toml", "--as", "manager"],
    seed=RequestContext(start_dir=squad, attachments={"r2.toml": "..."}))
# -> exit 1: Cannot read role override r2.toml: [Errno 2] No such file or directory
```

Related, local mode: the same read is relative to the process directory, not `client_cwd`, so `sq -C sub role add x --file r.toml` reads `./r.toml` while `sq -C sub task 1 body --file b.md` reads `sub/b.md`. The process-directory guard cannot see this (a relative `Path` open reads the cwd implicitly).

Fix direction: read role files through `read_client_text` (parse the returned text), and add `role add`/`role update` rows to the attachments table.
<!-- sq:finding:F1:body:end -->

#### Discussion

<!-- sq:finding:F1:discussion -->
- [2026-10-28T19:02:37Z] `python-dev` Elias Python:
  - Role add/update --file now read through the request: read_role_toml takes a reader, and the role commands pass common.read_client_file_text, so attachments are served, an unattached name is refused, and a relative name resolves under -C. The old error wording is kept. Rows for role add and role update join the attachments, -C and non-UTF-8 tables. Falsified: old read restored, 14 rows red; client_path bypassed, 5 -C rows red. The process-directory guard cannot be made to see this: whether an open is relative depends on a runtime value (a typer-supplied Path), so a static scan would only catch literals; the -C table is the guard.
- [2026-10-28T19:07:38Z] `reviewer` Paul Reviewer:
  - The core of the fix holds when checked through `sq` itself (dev-tree `run()` against a scratch squad, process directory elsewhere):
    
    - an unattached `--file r.toml` is refused with `error: cannot read file 'r.toml': it was not attached`, even though `r.toml` sits in the process directory;
    - an attached file is read; `role update --file` works the same way.
    
    Two shapes still fail. Both come from `--file` being typed `Path` on `role add` and `role update`, so the lookup key is `str(Path(value))`, not the value as the command line wrote it. ADR-1052 point 1 keys attachments "exactly as the command line writes it".
    
    1. **Normalised spellings are refused.** Each row attaches the file under the name exactly as written:
       - `--file ./r3.toml` → `error: cannot read file 'r3.toml': it was not attached`
       - `--file sub//r4.toml` → `error: cannot read file 'sub/r4.toml': it was not attached`
       - `--file sub/r5.toml/` → `error: cannot read file 'sub/r5.toml': it was not attached`
    
       `./file` is a common spelling, so in remote mode `sq role add x --file ./x.toml` would exit 1, where local mode succeeds. On native Windows, `Path` also rewrites `/` to `\`.
    2. **`--file -` behaves differently in the two modes.** Local mode reads a file named `-` (`error: Cannot read role override -: [Errno 2] No such file or directory: '-'`). A served request with stdin attached under `-` creates the role from stdin (exit 0). The forwarder attaches stdin whenever a client-file parameter is `-`, so the two modes disagree. The test that skips the `dash` shape for roles ("a role file named - is a file, not stdin") states the local rule, which the served path does not follow.
    
    Fix direction: declare the role `--file` as `str`, like every other `file_option` user, and look it up by the raw value. Then pick one meaning for `-`: stdin, as the shared help says for other commands, or a file in both modes. The forwarder's file-argument table must agree with whichever is chosen.
- [2026-10-28T19:17:00Z] `python-dev` Elias Python:
  - The role --file options are now str (metavar PATH kept), so the attachment is found under the name exactly as written (./r3.toml, sub//r4.toml, sub/r5.toml/). --file - reads stdin on role add and role update in both modes (served: the attached stdin; local: the process stdin); a file literally named - is now passed as ./-. Seen through sq: stdin role add and update work, ./- reads the file, -C sub resolves under sub, a non-UTF-8 role file gives the clean "not valid UTF-8" line. Surface cases in test_role.py: -C relative, --file - from stdin, non-UTF-8; each falsified (reader ignoring the client directory, dash read as a file, lax decode: red).
- [2026-10-28T19:20:25Z] `reviewer` Paul Reviewer:
  - Verified through sq on 4a4a30ae. In served requests, each file attached under the name as written is read: ./r3.toml, sub//r4.toml and sub/r5.toml/ each create their role (exit 0). An unattached r.toml is refused with the whole message. For --file -, stdin is read in both modes: served from the attachment (add and update) and local from stdin. ./- reads a file named -, served (attached as ./-) and local.
<!-- sq:finding:F1:discussion:end -->
<!-- sq:finding:F1:end -->

<!-- sq:finding:F2 -->
### F2 — Seeded terminal facts force_terminal and override the client's FORCE_COLOR/TTY_COMPATIBLE

<!-- sq:finding:F2:body -->
`build_console` passes `force_terminal=terminal.stdout_tty` (or `stderr_tty`) whenever terminal facts are seeded. An explicit `force_terminal` short-circuits Rich's `is_terminal`, so `FORCE_COLOR` and `TTY_COMPATIBLE` — both forwarded in the request's `env` by ADR-1052 point 1 — are ignored in a served request but honoured in local mode.

Repro (dev tree, scratch squad, `TERM=xterm-256color`, stdout redirected to a buffer):

```python
os.environ["FORCE_COLOR"] = "1"
run(["task", "7", "show"])                                  # local: ANSI present  -> True
run(["task", "7", "show"], seed=RequestContext(start_dir=squad, terminal=TerminalFacts()))
                                                            # seeded: ANSI present -> False
```

That is a remote/local output difference the ADR's byte-for-byte parity matrix would flag. Fix direction: let Rich detect against the environment and a stream that reports the client's `isatty` (the request scope's buffers, point 12), or pass `force_terminal` only when the facts say "terminal" and leave `None` otherwise.
<!-- sq:finding:F2:body:end -->

#### Discussion

<!-- sq:finding:F2:discussion -->
- [2026-10-28T19:02:40Z] `python-dev` Elias Python:
  - build_console no longer passes force_terminal. It wraps the stream in one that answers isatty with the client fact, so Rich applies TTY_COMPATIBLE and FORCE_COLOR before it, as in local mode; COLUMNS/LINES from the environment outrank the facts size. Rows for FORCE_COLOR, TTY_COMPATIBLE=0/1 against seeded facts added. Falsified with force_terminal restored: 3 rows red.
- [2026-10-28T19:09:37Z] `reviewer` Paul Reviewer:
  - Verified through sq. With FORCE_COLOR=1 and stdout piped, a seeded run is coloured, as a local run is. With a seeded terminal, TTY_COMPATIBLE=0 turns colour off, and a seeded pipe stays plain. The local parity matrix rerun against e0cfaea8 (14 commands x 6 environments x pty/pipe) gives 0 diffs out of 168 against the parent of 22ce7f65.
<!-- sq:finding:F2:discussion:end -->
<!-- sq:finding:F2:end -->

<!-- sq:finding:F3 -->
### F3 — Typer's help and usage-error consoles ignore seeded terminal facts

<!-- sq:finding:F3:body -->
Typer renders `--help` and click usage errors through its own consoles (`typer.rich_utils._get_rich_console`), not `console`/`err_console`. Those ignore the seeded `TerminalFacts` and take `FORCE_COLOR` from `typer.rich_utils.FORCE_TERMINAL`, which is computed once at import from the process environment, not the request's.

Repro (dev tree, scratch squad, seeded terminal `TerminalFacts(stdin_tty=True, stdout_tty=True, stderr_tty=True, columns=100, lines=40)`):

- `run(["task", "7", "show"], seed)` → ANSI present (our console honours the facts);
- `run(["--help"], seed)` → panels drawn, **no ANSI**;
- `run(["nosuch"], seed)` → exit 2, **no ANSI** on stderr.

Local mode under a pseudo-terminal gives ANSI for all three (checked with the dev-tree CLI). So help and usage errors would differ between the two modes for a terminal client, and a daemon started with `FORCE_COLOR` in its own environment would colour every client's help.

This cannot be fixed by forcing our consoles; it needs the request scope's stdio buffers to report the client's `isatty` (ADR point 12) and `FORCE_COLOR` handled per request. It may land with TASK-1218's scope — if so, defer it there with a parity row for `--help` and a usage error.
<!-- sq:finding:F3:body:end -->

#### Discussion

<!-- sq:finding:F3:discussion -->
- [2026-10-28T18:55:41Z] `tech-lead` Olivia Lead:
  - Deferred to TASK-1218 ST9 (written body names this finding). The fix needs the request scope stdio buffers to report the client isatty and a per-request colour decision for Typer consoles, which only exist in the daemon; local mode is byte-identical (your 168-run parity). ST9 carries the parity rows you asked for: --help, sub-command --help and a usage error, terminal and pipe clients, plus a FORCE_COLOR daemon.
- [2026-10-28T19:08:38Z] `reviewer` Paul Reviewer:
  - The deferral has a real home: TASK-1218 ST9 states the fix (stdio buffers that report the client isatty, colour per request) and parity rows for help and usage errors.
- [2026-10-28T22:31:12Z] `reviewer` Paul Reviewer:
  - Subject gone; no fix will be made. ADR-1225 (Accepted) replaces the command endpoint with resource routes, and its section 9 removes the seeded terminal facts and `run`'s seed. TASK-1227 ST4 deletes that code. In remote mode the CLI is the client process: it parses, renders and prints `--help` and usage errors itself, so Typer's consoles read the user's own stdio and environment, exactly as in local mode (ADR-1225 section 5; Consequences: "the renderer always runs in the user's own process"). The daemon builds no consoles (section 7). No concern survives in another form: help and usage errors never make a call, so the mode-parity job has nothing to compare for them. Deferral re-pointed from TASK-1218 ST9, which now holds the schema and vocabulary checks, to TASK-1227, which removes the subject. The lifecycle has no edge out of Deferred, so this stays Deferred rather than WontFix.
- [2026-10-28T23:29:09Z] `reviewer` Paul Reviewer:
  - Disposition: subject removed, nothing left to fix. ADR-1225 section 9 dropped the seeded terminal facts, NeedsTerminal and the signalling prompt helpers; commit 3b3cfbd9 (TASK-1227) removed them. Verified on that commit: no reference to TerminalFacts, NeedsTerminal, confirm_or_signal, prompt_or_signal or attachments remains in src or tests, build_consoles takes no terminal, and the four prompt sites are plain typer.confirm/typer.prompt again (each asked and wrote nothing when answered n under a pseudo-terminal). Left Deferred, which has no outgoing transition; this comment is the closing record (REV-1235).
- [2026-10-29T16:23:47Z] `reviewer` Paul Reviewer:
  - Noted: subject removed, nothing to fix. 5f5ef259 (TASK-1227; the rebased 3b3cfbd9 cited above) deleted TerminalFacts, NeedsTerminal and the signalling prompts; at HEAD none remains in src or tests, build_consoles takes no terminal, and every prompt is a typer.confirm/prompt in _cli. Forced from Deferred per op-pierre 2e3799b.
<!-- sq:finding:F3:discussion:end -->
<!-- sq:finding:F3:end -->

<!-- sq:finding:F4 -->
### F4 — No test covers terminal facts reaching the consoles; build_consoles(None) mutation survives

<!-- sq:finding:F4:body -->
No test exercises the terminal-facts path into the consoles (`TerminalFacts` → `build_console`'s `force_terminal`/`width`/`height`). Mutation: in `main_callback`, `consoles=common.build_consoles(prior.terminal)` → `common.build_consoles(None)`. Result: `tests/cli/test_in_process_entry.py` stays **47 passed**. The width isolation row uses `COLUMNS`, which a plain `Console()` reads anyway.

ST2's acceptance is "consoles built per invocation … from the terminal facts". Add rows that seed a terminal (tty true/false × a width) and assert colour presence and wrapped width on stdout and stderr; with finding 2 fixed, include a `FORCE_COLOR` row.
<!-- sq:finding:F4:body:end -->

#### Discussion

<!-- sq:finding:F4:discussion -->
- [2026-10-28T19:02:42Z] `python-dev` Elias Python:
  - Added rows seeding terminal facts: colour on stdout and stderr per tty fact (4 rows), the colour environment against the facts (4 rows), and width from env then facts (3 rows). Falsified with build_consoles(None) in main_callback: 5 rows red.
- [2026-10-28T19:08:34Z] `reviewer` Paul Reviewer:
  - Not verified on its own. The new colour and width rows exist and fail when the facts are dropped, but they live in test_in_process_entry.py, which F10 says must be rewritten under ADR-1172. This finding is carried by F10 and settles with it. Through sq, the terminal facts now reach the consoles: a seeded terminal is coloured, a seeded pipe is not, the facts width of 50 is honoured, and COLUMNS=70 wins over it.
- [2026-10-28T19:20:30Z] `reviewer` Paul Reviewer:
  - The colour and width tests went with the deleted module. Terminal facts reaching the consoles is now a case in TASK-1218 ST10 (terminal client vs pipe client).
- [2026-10-28T22:31:13Z] `reviewer` Paul Reviewer:
  - Subject gone; no fix will be made. The finding asked for tests of `TerminalFacts` reaching the consoles. ADR-1225 section 9 removes terminal facts as a request seed, and TASK-1227 ST4 deletes them; consoles stay built per invocation from the process's own stdio, which the existing surface tests already drive (the `forced_terminal` fixture with `TTY_COMPATIBLE`). The TASK-1218 ST10 case this finding pointed to no longer exists: ST10 now holds the OpenAPI document and route guards. Deferral re-pointed to TASK-1227. The lifecycle has no edge out of Deferred, so this stays Deferred rather than WontFix.
- [2026-10-28T23:29:10Z] `reviewer` Paul Reviewer:
  - Disposition: subject removed, nothing left to fix. ADR-1225 section 9 dropped the seeded terminal facts, NeedsTerminal and the signalling prompt helpers; commit 3b3cfbd9 (TASK-1227) removed them. Verified on that commit: no reference to TerminalFacts, NeedsTerminal, confirm_or_signal, prompt_or_signal or attachments remains in src or tests, build_consoles takes no terminal, and the four prompt sites are plain typer.confirm/typer.prompt again (each asked and wrote nothing when answered n under a pseudo-terminal). Left Deferred, which has no outgoing transition; this comment is the closing record (REV-1235).
- [2026-10-29T16:23:49Z] `reviewer` Paul Reviewer:
  - Noted: subject removed, nothing to fix. 5f5ef259 (TASK-1227; the rebased 3b3cfbd9 cited above) deleted TerminalFacts, NeedsTerminal and the signalling prompts; at HEAD none remains in src or tests, build_consoles takes no terminal, and every prompt is a typer.confirm/prompt in _cli. Forced from Deferred per op-pierre 2e3799b.
<!-- sq:finding:F4:discussion:end -->
<!-- sq:finding:F4:end -->

<!-- sq:finding:F5 -->
### F5 — Override remedy path still spelled from the process directory in a served request

<!-- sq:finding:F5:body -->
`path_from_process_dir` gained a `base` and the roster remedy passes `get_context().start_dir`, but the second caller — `_overrides/_service.py` (the "role override has no role under it" issue `sq check` prints) — still uses the default, the process directory. In a served request the remedy path is spelled relative to the serving process's directory.

Repro (scratch squad with `squads/.overrides/roles/ghost.toml`, process cwd a sibling directory):

- local, from the squad: `` `sq role add ghost --file squads/.overrides/roles/ghost.toml` ``
- `run(["check"], seed=RequestContext(start_dir=squad))` from the sibling: `` `sq role add ghost --file ../sq1/squads/.overrides/roles/ghost.toml` ``

Fix direction: have `path_from_process_dir` default to the context's `start_dir` when set (one place), rather than threading `base` per caller; a defaulted parameter is how the next caller gets missed.
<!-- sq:finding:F5:body:end -->

#### Discussion

<!-- sq:finding:F5:discussion -->
- [2026-10-28T19:02:45Z] `python-dev` Elias Python:
  - path_from_process_dir now defaults to the context start_dir in one place (the base parameter and the per-caller argument are gone; _paths gains an edge to _context, recorded in the edge table). Test runs check from a sibling directory and asserts the remedy path. Falsified with the default removed: 1 row red.
- [2026-10-28T19:08:30Z] `reviewer` Paul Reviewer:
  - Verified through sq: with the start directory set to the squad and the process directory a sibling, the sq check remedy reads `sq role add ghost --file squads/.overrides/roles/ghost.toml`, the same as a local run from the squad (it was `../sq1/...` before the fix).
<!-- sq:finding:F5:discussion:end -->
<!-- sq:finding:F5:end -->

<!-- sq:finding:F6 -->
### F6 — Prompt after a committed transaction does not fail as ADR-1052 point 12 states

<!-- sq:finding:F6:body -->
ADR-1052 point 12: "if a transaction has already committed in the request, the prompt fails the command with an error instead". `confirm_or_signal`/`prompt_or_signal` always raise `NeedsTerminal`; nothing checks whether a write already committed. The developer's handback says this was left out on purpose.

Today every prompt site asks before it writes, and the per-site ordering tests pin that. So this is a safety net for future prompt sites, not a live bug. If it ever fires, the client re-runs a command that has already partly committed. Either build the check in the helper (the index store knows whether a transaction committed in this request) or record on the ADR that the ordering tests are the only guard.
<!-- sq:finding:F6:body:end -->

#### Discussion

<!-- sq:finding:F6:discussion -->
- [2026-10-28T18:55:38Z] `tech-lead` Olivia Lead:
  - Deferred to TASK-1218 ST8, which builds the post-commit check in the request scope: a request-scoped flag set by the commit path of IndexStore.transaction(), and a NeedsTerminal raised after a commit becomes an error, not 503 needs_terminal. Until then the per-site ask-before-write pins in TASK-1217 are the guard.
- [2026-10-28T19:08:39Z] `reviewer` Paul Reviewer:
  - The deferral has a real home: TASK-1218 ST8 states the flag recorded on commit, the error exit, and a test that commits then prompts.
- [2026-10-28T22:31:15Z] `reviewer` Paul Reviewer:
  - Subject gone; no fix will be made. The hazard was a `NeedsTerminal` raised after a write had committed, which would make the client re-run a partly committed command. ADR-1225 section 3 drops `needs_terminal`, section 8 removes ADR-1052 point 12's prompt branch, and section 9 turns `confirm_or_signal`/`prompt_or_signal` back into `typer.confirm`/`typer.prompt`; TASK-1227 ST4 does the removal. Prompts now run in the CLI between calls, and an operation never prompts, so there is no re-run to make unsafe. Checked on bb306416: all four prompt sites are in `_cli` (`_items.py` x2, `_common.py` comment removal, `_main.py`); none is in `_services`. What remains is the ordinary ask-before-write rule, which TASK-1229 states for removals ("prompts sit between calls, never inside one") and which its own review checks. TASK-1218 ST8 now holds the request scope and headers, not a post-commit flag. Deferral re-pointed to TASK-1227. The lifecycle has no edge out of Deferred, so this stays Deferred rather than WontFix.
- [2026-10-28T23:29:11Z] `reviewer` Paul Reviewer:
  - Disposition: subject removed, nothing left to fix. ADR-1225 section 9 dropped the seeded terminal facts, NeedsTerminal and the signalling prompt helpers; commit 3b3cfbd9 (TASK-1227) removed them. Verified on that commit: no reference to TerminalFacts, NeedsTerminal, confirm_or_signal, prompt_or_signal or attachments remains in src or tests, build_consoles takes no terminal, and the four prompt sites are plain typer.confirm/typer.prompt again (each asked and wrote nothing when answered n under a pseudo-terminal). Left Deferred, which has no outgoing transition; this comment is the closing record (REV-1235).
- [2026-10-29T16:23:51Z] `reviewer` Paul Reviewer:
  - Noted: subject removed, nothing to fix. 5f5ef259 (TASK-1227; the rebased 3b3cfbd9 cited above) deleted TerminalFacts, NeedsTerminal and the signalling prompts; at HEAD none remains in src or tests, build_consoles takes no terminal, and every prompt is a typer.confirm/prompt in _cli. Forced from Deferred per op-pierre 2e3799b.
<!-- sq:finding:F6:discussion:end -->
<!-- sq:finding:F6:end -->

<!-- sq:finding:F7 -->
### F7 — Attachments decoded outside the CLI; invalid UTF-8 --file escapes as a traceback

<!-- sq:finding:F7:body -->
Two related points on how attached file content is decoded.

1. **Attachments are `Mapping[str, str]`,** so decoding happens before the CLI sees them. ADR-1052 point 1 says attachments are bytes "because local mode decodes them itself", with the CLI decoding `--file` as UTF-8 the way `client_path` does and stdin through a text stream with the client's encoding. With `str`, whatever builds the seed (TASK-1218) must reproduce `read_text`'s universal-newline translation (CRLF → LF), its error behaviour, and the stdin encoding, or the two modes store different bodies. Keeping bytes in the context and decoding in `read_client_text` keeps one decoder.
2. **Not new in this change, but on the touched function:** a `--file` that is not valid UTF-8 escapes as an uncaught `UnicodeDecodeError` traceback. `read_client_text` catches only `OSError`. Reproduced with the parent commit and this one: `sq task 7 body --file bad.md` (bytes `ok\xff\xfe`) → exit 1 with a Rich traceback. The ADR relies on "a file that is not valid UTF-8 fails the same way in both modes", which should be a clean `SquadsError`.
<!-- sq:finding:F7:body:end -->

#### Discussion

<!-- sq:finding:F7:discussion -->
- [2026-10-28T19:02:47Z] `python-dev` Elias Python:
  - Attachments are Mapping[str, bytes]. read_client_bytes serves them; one decoder (a text stream, so newlines translate as a file read does) turns bytes into text, stdin through sys.stdin.encoding. A non-UTF-8 file is a SquadsError naming the file in both modes for body, comment, import and role files, never a traceback (role files keep the existing "not valid UTF-8" wording). Falsified: lax decoding turned 10 rows red; no newline translation turned the CRLF row red.
- [2026-10-28T19:08:32Z] `reviewer` Paul Reviewer:
  - Verified through sq, with attachments in a served request compared against local files and stdin. CRLF in a file and on stdin is stored as LF in both modes. A BOM is kept as U+FEFF in both, as before. An empty file stores an empty body in both. Stdin in latin-1, with the client encoding latin-1, decodes as café. Invalid UTF-8 and a UTF-16 file give one clean error line: cannot read file NAME: not valid utf-8 (invalid start byte at byte N), exit 1, in both modes; local stdin gives the same message. Attachments are now bytes.
<!-- sq:finding:F7:discussion:end -->
<!-- sq:finding:F7:end -->

<!-- sq:finding:F8 -->
### F8 — Comment-removal listing before NeedsTerminal; vacuous --version stderr row

<!-- sq:finding:F8:body -->
Two minor points; nothing to fix in this task.

- Comment removal prints the matching comments to `console` before `confirm_or_signal` raises `NeedsTerminal`. When the daemon (TASK-1218) catches the signal, it must discard that request's buffered stdout and stderr before answering `needs_terminal`, or the listing appears twice once the client re-runs locally.
- In `test_the_entry_returns_the_exit_code_a_local_run_ends_with`, the `--version` row has `err_has=""`, which `"" in err` always satisfies, and stdout is not checked. The row proves only the exit code.
<!-- sq:finding:F8:body:end -->

#### Discussion

<!-- sq:finding:F8:discussion -->
- [2026-10-28T18:55:42Z] `tech-lead` Olivia Lead:
  - First point (comment-removal listing before NeedsTerminal) is homed in TASK-1218 ST8: the scope discards the request buffered stdout/stderr before answering needs_terminal, with a test that the listing prints once. Second point (vacuous --version stderr row) stays with @python-dev in TASK-1217, so the finding stays Open until that row is fixed.
- [2026-10-28T19:02:49Z] `python-dev` Elias Python:
  - Second half fixed: the --version row now asserts stdout starts with "squads " and stderr is empty. Falsified by reasoning only: the old assertion held for any stderr; the new one fails on any stderr output.
- [2026-10-28T19:08:35Z] `reviewer` Paul Reviewer:
  - Both points now have a home. Point 1 (discard buffered output on NeedsTerminal) is on TASK-1218 ST8, which states the discard and its test. Point 2 (the vacuous --version row) was edited inside test_in_process_entry.py, so it is carried by F10 rather than verified.
- [2026-10-28T19:17:05Z] `python-dev` Elias Python:
  - The vacuous --version stderr row went with test_in_process_entry.py (deleted); nothing remains of it.
- [2026-10-28T22:31:16Z] `reviewer` Paul Reviewer:
  - Point 1's subject is gone: there is no daemon-side stdout buffer to discard and no client re-run, because ADR-1225 removes `needs_terminal` and stdio redirection (sections 3 and 7; TASK-1227 ST4 removes `NeedsTerminal`). The concern survives in one form, output printed before a prompt: `comment remove` without `--yes` becomes a preview call that lists the comments with their full hashes, a confirmation in the CLI, then the remove call (ADR-1225 section 3, "comment remove after a confirmation"). TASK-1229 builds that flow, so the listing must print once, before the prompt, and nothing must print or be removed after a refusal. Re-pointed from TASK-1218 ST8 (now the request scope and headers) to TASK-1229, to check in its review. Point 2 (the vacuous `--version` row) went with the deleted test module and needs nothing.
- [2026-10-28T23:29:12Z] `reviewer` Paul Reviewer:
  - Disposition: subject removed, nothing left to fix. ADR-1225 section 9 dropped the seeded terminal facts, NeedsTerminal and the signalling prompt helpers; commit 3b3cfbd9 (TASK-1227) removed them. Verified on that commit: no reference to TerminalFacts, NeedsTerminal, confirm_or_signal, prompt_or_signal or attachments remains in src or tests, build_consoles takes no terminal, and the four prompt sites are plain typer.confirm/typer.prompt again (each asked and wrote nothing when answered n under a pseudo-terminal). Left Deferred, which has no outgoing transition; this comment is the closing record (REV-1235).
- [2026-10-29T16:23:53Z] `reviewer` Paul Reviewer:
  - Verified at HEAD: c459d709 (TASK-1229) built comment remove as preview call, CLI prompt, then remove call. Scratch squad: without --yes, answered n, the listing prints once before the prompt, nothing after Aborted, and the comment stays. Forced from Deferred per op-pierre 2e3799b.
<!-- sq:finding:F8:discussion:end -->
<!-- sq:finding:F8:end -->

<!-- sq:finding:F9 -->
### F9 — Local-mode changes from the fix have no CHANGELOG entry: role --file under -C, clean non-UTF-8 refusal

<!-- sq:finding:F9:body -->
The fix changes two things an adopter sees in **local** mode, and neither is in the CHANGELOG's unreleased section. TASK-1217 also says that nothing adopter-facing moves.

1. **`sq role add|update --file` now resolves a relative path under `-C`.** Checked on a scratch squad that holds `rc.toml` and `sub/rc.toml`, each naming a different role, running `sq -C sub role add … --file rc.toml`:
   - parent commit: `added Process Dir` (reads `./rc.toml`, from the process directory);
   - this commit: `added Under C` (reads `sub/rc.toml`).

   This matches how `body --file` already behaves, so it reads as a fix. But it changes which file is read.
2. **A `--file` that is not valid UTF-8 is now a clean error** (`error: cannot read file '…': not valid utf-8 (invalid start byte at byte 2)`, exit 1) instead of a traceback, for body, comment, import, memory, board and stdin.

Both need a CHANGELOG entry, written by the technical writer. The task's "no adopter-facing change" line should be amended to name them.
<!-- sq:finding:F9:body:end -->

#### Discussion

<!-- sq:finding:F9:discussion -->
- [2026-10-28T19:20:15Z] `tech-writer` Theo Writer:
  - CHANGELOG [0.18.0] entries added. Changed: `--file -` on `sq role add` / `sq role <slug> update` reads stdin, a file named - is passed as ./-. Fixed: role --file resolves a relative path under -C; a non-UTF-8 --file (body, sub-entity body, comment, import, memory, board, and stdin via --file -) exits 1 with one error line instead of a traceback. Each verified on the dev tree against a scratch squad, and the before behaviour against the released 0.17.0. Role definition files already refused non-UTF-8 cleanly in 0.17.0, so the entry says so rather than claiming a change.
- [2026-10-28T19:21:09Z] `reviewer` Paul Reviewer:
  - Verified against my probes. The uncommitted CHANGELOG [0.18.0] entries match the observed behaviour: role --file under -C (parent commit read ./rc.toml, now sub/rc.toml), --file - as stdin with ./- naming a file, and a clean non-UTF-8 error for body, comment, import, memory, board and stdin. The role-file message is not quoted, so F11 does not touch the entry.
<!-- sq:finding:F9:discussion:end -->
<!-- sq:finding:F9:end -->

<!-- sq:finding:F10 -->
### F10 — test_in_process_entry.py breaks ADR-1172 rules 3-5: direct run()/unit calls, file reads, no covers

<!-- sq:finding:F10:body -->
Operator ruling on TASK-1217: tests follow ADR-1172, which means CLI surface tests only. `tests/cli/test_in_process_entry.py` (453 lines, 22 test functions) breaks rules 3–5:

- **Rule 3 (coverage declared by `covers`):** the module has no `covers` marker, so the coverage guard and the marker check in the `invoke` fixture never see it.
- **Rule 4 (in-process through the `runner`/`invoke` fixtures):** every case calls `squads._cli.run(argv, seed=…)` directly through a private `ran` fixture instead of `invoke`. `test_an_attached_file_reads_the_way_a_file_on_disk_does` calls `read_client_text` and `bind_context` as units. `test_nothing_a_command_binds_survives_in_the_callers_context` compares `get_context()` before and after a run. The `stdin` fixture monkeypatches `sys.stdin` instead of passing input through the runner.
- **Rule 5 (assert what the user sees, state read back through the CLI):** `_tree()` reads every file under the squad (`rglob` + `read_bytes`) to prove nothing was written, in the refusal, prompt-ordering and init cases. Several assertions are substrings: `err_has in result.err` in the exit-code table, `"UTF-8" in result.err or "utf-8" in result.err` and `"Traceback" not in result.err` in the decode case, and ESC presence in the colour rows.

**Observable through today's `sq` surface in local mode** (can become `invoke` cases with `covers`):

- `role add`/`role update --file` read relative to the `-C` directory (`""`/`-C` against `role add --file`, `role update --file`);
- a `--file` that is not valid UTF-8 refused with the whole error line, for each `file_option` command and `import`'s file argument;
- `--file -` read from stdin, and CRLF in a file or on stdin stored as LF (read back with `show --json`);
- the `sq check` override remedy path spelled from the starting directory;
- local prompts: `remove` asks, `--yes` skips. These are probably already declared in the item, sub-entity and comment modules, so check before adding.

**Observable only through the daemon's command endpoint** (TASK-1218, and the forwarder in TASK-1219). These are not surface cases today, so they belong with the endpoint's tests once it exists, not as calls into `run()`:

- the request's starting directory (`start_dir`) and `-C` resolved against it;
- attachments served, refused when not attached, keyed by the name as written, and stdin decoded with the client's encoding;
- terminal facts deciding colour and width, and the client's `FORCE_COLOR`/`TTY_COMPATIBLE`/`COLUMNS` winning;
- `NeedsTerminal` at each prompt site before any write, and `init` signalling;
- isolation between commands served by one process (clock, actor, `-C`, consoles, output).

F4 (terminal-facts coverage) and the second point of F8 (the vacuous `--version` row) were fixed inside this module, so they are carried by this finding and are not verified on their own.

**Size.** The suite is bounded because ADR-1172 exists, so cross products and repeated cases count as defects in this review. The module collects **93 cases**, and 70 of them come from tables over one shared reader:

- three tables of `FILE_COMMANDS` (body, comment, import, role add, role update) × shape (relative, absolute, `-`), 15 cases each, 45 in total;
- the UTF-8 table, 5 commands × local/served, 10 cases;
- the `-C` table, 5 cases;
- colour and width tables, 11 cases;
- a 5-row exit-code table.

`read_client_text` is one reader shared by every command (rule 2: a shared mechanism is tested once, on one host). The shapes are not interacting parameters (rule 1).

**What a surface rewrite keeps in `tests/cli`:** about **5 cases**, each one behaviour plus its refusal, folded into the existing group modules rather than a new module:

- `role add --file` read under `-C` (test_role.py);
- a non-UTF-8 `--file` refused, on one host (`task body --file`), with the whole error line;
- a role definition file that is not UTF-8 refused, because it goes through a separate reader;
- a CRLF file stored as LF, read back through `show --json`;
- the `sq check` remedy path.

Exit codes, `--file -` and the prompts are already covered by the existing modules, so they add none.

**What goes to TASK-1218's endpoint tests:** about **13–15 cases**, one per behaviour: start directory, `-C` against it, attachment served, attachment refused, stdin encoding, colour from terminal facts, width from terminal facts, the client's environment winning, isolation as one sequence, and one `NeedsTerminal`-before-write case per prompt site, as ADR-1052 point 12 requires.

**The rest, about 73 cases, should be dropped.**
<!-- sq:finding:F10:body:end -->

#### Discussion

<!-- sq:finding:F10:discussion -->
- [2026-10-28T19:17:02Z] `python-dev` Elias Python:
  - test_in_process_entry.py (93 tests) is deleted. Kept as surface cases with covers markers, through invoke: role add --file under -C, role add --file - from stdin, role add --file non-UTF-8 (test_role.py); body --file non-UTF-8 (test_item_verbs.py). A CRLF case was dropped: it stays green when the decoder stops translating newlines, because the body is normalised downstream, so it proved nothing at this surface. The remedy-path case is dropped: locally the start directory is the process directory, so nothing differs. The seeded cases move to TASK-1218 as endpoint tests.
- [2026-10-28T19:20:28Z] `reviewer` Paul Reviewer:
  - Verified. test_in_process_entry.py is deleted. The four kept cases go through invoke, carry covers markers and assert whole lines; they pass. I falsified two myself: reading the role file from the process directory turns the -C case and the dash case red, and no longer catching UnicodeDecodeError turns the body non-UTF-8 case red. The remedy-path drop is right: locally the start directory is the process directory, and the case lives in TASK-1218 ST10. The CRLF drop is right under rule 5, but the stated reason is inexact. A decoder that does not translate newlines leaves CR bytes in the item file (2 lines, checked against a mutant). show --json hides them because the read path translates them. So the defect is real but cannot be seen at this surface; it is not normalised on write.
<!-- sq:finding:F10:discussion:end -->
<!-- sq:finding:F10:end -->

<!-- sq:finding:F11 -->
### F11 — A role definition file that is not UTF-8 is reported as a role override

<!-- sq:finding:F11:body -->
sq role add scout --file bad.toml, with a file that is not valid UTF-8, prints "error: Role override bad.toml is not valid UTF-8; save it as UTF-8 and re-run." The --file of role add and role update is a role definition, not a file under .overrides/roles/. The wording comes from ROLE_OVERRIDE_MESSAGES, which read_role_toml reuses, and the new kept case in test_role.py now pins it. Every other --file says "cannot read file NAME: ...". The wording predates this change, but the test makes it the asserted contract. Fix direction: give role definition files their own messages, or route them through the read_client_text wording.
<!-- sq:finding:F11:body:end -->

#### Discussion

<!-- sq:finding:F11:discussion -->
- [2026-10-28T19:23:29Z] `python-dev` Elias Python:
  - A --file role definition that is not UTF-8 now reads "cannot read role file 'bad.toml': not valid utf-8 (invalid start byte at byte 12)", built by the same helper (not_text_refusal) as the body/comment/import refusals. Override files under .overrides/ keep "Role override ...". Other --file failures (missing file, malformed TOML) keep their existing wording because existing tests pin them. Falsified: removing the conversion turns the kept test red.
- [2026-10-28T19:24:47Z] `tech-writer` Theo Writer:
  - CHANGELOG [0.18.0] Fixed, non-UTF-8 --file entry corrected: role add/update --file now says `error: cannot read role file NAME: not valid utf-8 (…)` in place of the 0.17.0 `Role override NAME is not valid UTF-8; save it as UTF-8 and re-run.`, and a file under .overrides/roles/ keeps the Role override message. Verified on the dev tree (file and --file -) and against 0.17.0.
- [2026-10-28T19:25:50Z] `reviewer` Paul Reviewer:
  - Verified through sq on 16658673, served and local. role add and role update with bad.toml, ./sub/bad.toml, an absolute path, ./x//bad.toml (served, attached as written) and - (local stdin, served attachment) all exit 1 with: error: cannot read role file 'NAME': not valid utf-8 (invalid start byte at byte N), with NAME as written. An .overrides/roles/ file keeps the Role override wording, both in role show and in sq check. The kept test's expected line and the a56e92bb CHANGELOG sentence match what I observed.
<!-- sq:finding:F11:discussion:end -->
<!-- sq:finding:F11:end -->

<!-- sq:finding:F12 -->
### F12 — role --file read errors still mix wordings: a missing file says role override, an unattached one says file

<!-- sq:finding:F12:body -->
Same command, same option, three wordings (16658673, dev tree):
- not UTF-8: error: cannot read role file 'bad.toml': not valid utf-8 (invalid start byte at byte 13)
- missing (local): error: Cannot read role override missing.toml: [Errno 2] No such file or directory: 'missing.toml'
- not attached (served): error: cannot read file 'bad.toml': it was not attached

The missing-file line has the same cause as F11: an OSError still goes through read_override_text and ROLE_OVERRIDE_MESSAGES, so a role definition file is called a role override, with a capital C and a repeated errno. The served refusal passes no what, so it says file rather than role file. Fix direction: in _read_definition, convert OSError the same way as the decode error (cannot read role file NAME: No such file or directory), and pass what=role file into read_client_file_text so the attachment refusal matches. Pre-existing wording, low.
<!-- sq:finding:F12:body:end -->

#### Discussion

<!-- sq:finding:F12:discussion -->
- [2026-10-28T19:27:40Z] `python-dev` Elias Python:
  - Every read failure of a role --file definition now goes through the same funnel as body/comment/import, naming it a role file, in local and served mode: missing or unreadable "cannot read role file <name>: <reason>", not UTF-8 "cannot read role file <name>: not valid utf-8 (...)", not attached "cannot read role file <name>: it was not attached". Malformed TOML, invalid definitions and .overrides/ role files keep their wording. The two role tests pinning the missing-file line were updated, no cases added. Falsified: reading through the plain file reader turns 3 role tests red.
- [2026-10-28T19:28:57Z] `tech-writer` Theo Writer:
  - CHANGELOG [0.18.0] Fixed, non-UTF-8 --file entry now says role add/update --file refusals read like the other --file ones: missing file `cannot read role file NAME: No such file or directory` (was `Cannot read role override NAME: [Errno 2] …`), non-UTF-8 as before. Missing-file case verified on the dev tree (add and update) and against 0.17.0.
- [2026-10-28T19:29:14Z] `reviewer` Paul Reviewer:
  - Verified through sq on 7a6cd237. Local, every read failure gives cannot read role file NAME: REASON, for role add and role update: a missing file (No such file or directory), a directory (Is a directory), mode 000 (Permission denied), not UTF-8, and - with bad stdin. Served, the same wording covers not attached, no stdin attached and not UTF-8. Nothing else broke: -C sub, ./a//ok.toml attached as written, and - from an attachment all create the role, and .overrides/ files keep the Role override wording. The CHANGELOG [0.18.0] entry matches the missing-file and non-UTF-8 lines I observed.
<!-- sq:finding:F12:discussion:end -->
<!-- sq:finding:F12:end -->

<!-- sq:finding:F13 -->
### F13 — Retirement and vocabulary checks run before a request queues, not before it runs

<!-- sq:finding:F13:body -->
`Application.check_client` (`_daemon/_app.py`) runs the retirement check, and the vocabulary check after it, when the request arrives, before `RequestScope.run` takes the one `asyncio.Lock`. A request queued behind another therefore runs on a configuration that changed while it waited. ADR-1052 point 13: "Before running each command it compares the fingerprint", and `sq override` and `sq migrate up` through the daemon are exactly the operations that change it for the request queued behind them.

Driven at 9f01c537 with the harness (`serve_squad` with a flag as the retirement check): an external OS lock held, request 1 (`POST /v1/items`) sent and waiting on it, request 2 (`GET /v1/items`) sent and queued, then the flag set and the lock released. Request 2 answered `200` with the listing; it should have answered `503 {"not_executed": "retiring"}`.

Fix: run the retirement and vocabulary checks inside the scope, after the lock is taken and before the handler (the schema check can stay ahead of the queue: it needs no squad state). One route case: a request queued behind a held lock, configuration changed before its turn, answers `retiring`.
<!-- sq:finding:F13:body:end -->

#### Discussion

<!-- sq:finding:F13:discussion -->
<!-- sq:finding:F13:discussion:end -->
<!-- sq:finding:F13:end -->

<!-- sq:finding:F14 -->
### F14 — Single-item reads of sub-entity lists, refs and roster entries answer no ETag

<!-- sq:finding:F14:body -->
The rule "ETag only where the handler read or wrote the addressed file" is a sound mechanism (no re-read after commit, and the read, the compare and the write tag share one reader), but it leaves single-item reads without an `ETag`. Driven at 9f01c537:

- `GET /v1/items/{id}/subentities`: no ETag. ADR-1225 §3 names "`GET /v1/items/{id}` and the sub-entity routes under it". (`…/subentities/ST1` and `…/comments` do carry one.)
- `GET /v1/items/{id}/refs`: no ETag, though adding and removing a ref compare `If-Match`.
- `GET /v1/roles/{addr}` (and the skill and operator show): no ETag, though `PATCH /v1/roles/{addr}` compares `If-Match` ("every single-item read"; "the same rule covers role, skill and operator"). A web front editing a role has to read it through `/v1/items/ROLE-1` to get the tag.

Also, the OpenAPI document declares the `ETag` response header on every non-`DELETE` operation and on no `DELETE`, but `DELETE /v1/items/{id}/refs/{target}` answers with one.

Fix: those handlers note the addressed item's read (`_address` plus a read through `_read_item_file`), and the OpenAPI document declares the header from the same rule the endpoint follows.
<!-- sq:finding:F14:body:end -->

#### Discussion

<!-- sq:finding:F14:discussion -->
<!-- sq:finding:F14:discussion:end -->
<!-- sq:finding:F14:end -->

<!-- sq:finding:F15 -->
### F15 — skills link-role and unlink-role ignore If-Match

<!-- sq:finding:F15:body -->
`skills.link_role` and `skills.unlink_role` add or drop a `scopes` ref on the skill's file, but they are not in `CONDITIONAL_WRITES` (`_api/_ops.py`). ADR-1225 §3 lists "refs" among the checked writes, "for items and roster entries alike". Driven at 9f01c537: `POST /v1/skills/probe-skill/link-role` with a stale `If-Match` answered `200` and changed 8 files, where `skills.ref_add` with the same stale tag answers `409 changed_since_read`.

Fix: add both to `CONDITIONAL_WRITES` (the guard already checks that every member is a non-GET operation of the table).
<!-- sq:finding:F15:body:end -->

#### Discussion

<!-- sq:finding:F15:discussion -->
<!-- sq:finding:F15:discussion:end -->
<!-- sq:finding:F15:end -->

<!-- sq:finding:F16 -->
### F16 — GET-no-mutate case samples 12 of 53 GETs; two cases assert part of the response

<!-- sq:finding:F16:body -->
Two kinds of route case are weaker than ADR-1172 "The daemon's routes" asks.

- `test_get_requests_leave_every_file_of_the_squad_as_they_found_it` calls 12 of the table's 53 `GET` operations. Falsified on a scratch export: a file write injected after `items.list` turns it red; the same write after `workload` or `items.refs` leaves it green. A probe that called all 53 (with a seeded item, sub-entity, comments, skill, operator, memory and notice) changed no file, so the property holds today. The case should iterate the `GET` operations of the table, so a new one is covered without an edit.
- `test_a_transition_the_lifecycle_refuses_answers_409_conflict` asserts substrings of the message, and `test_a_partial_read_answers_200_with_what_it_left_out` asserts only the rows' `body`. ADR-1172 rule 5 and its routes section ask for the whole response.
<!-- sq:finding:F16:body:end -->

#### Discussion

<!-- sq:finding:F16:discussion -->
<!-- sq:finding:F16:discussion:end -->
<!-- sq:finding:F16:end -->

<!-- sq:finding:F17 -->
### F17 — Stream guard misses indirect writers; the daemon logger writes a 500 to stderr

<!-- sq:finding:F17:body -->
The stream guard (`tests/meta/test_nothing_below_the_cli_writes_to_the_process_streams.py`) matches `sys` stream names and bare `print`. Falsified on a scratch export by appending to `_index/_reflog.py`: `print(..., file=sys.stderr)`, `from sys import stderr as _e` and `sys.__stderr__` turn it red; `os.write(2, b"x")` and `rich.console.Console(stderr=True)` leave it green.

The live case is `_daemon/_app.py`: `_log.error("unhandled error in a request", exc_info=exc)` on a 500. The logger has no handler, so logging's last-resort handler writes the traceback to `sys.stderr`. In the in-process parity run (TASK-1219) that lands in the captured output the guard exists to keep clean. The 500 route case passes only because `caplog` attaches a handler.

Fix: lane B's lifecycle gives the `squads.daemon` logger its log-file handler with `propagate=False`, and the harness does the same; the guard also flags `Console(` and `os.write(` below the CLI.
<!-- sq:finding:F17:body:end -->

#### Discussion

<!-- sq:finding:F17:discussion -->
<!-- sq:finding:F17:discussion:end -->
<!-- sq:finding:F17:end -->

<!-- sq:finding:F18 -->
### F18 — Lane A wire decisions to record in ADR-1225

<!-- sq:finding:F18:body -->
Lane A made six wire decisions that ADR-1225 does not state yet. I confirm each as built; they belong in sections 2 and 3, so TASK-1219 and TASK-1221 build on the record.

1. **ETag over text, not bytes.** The tag is the SHA-256 of the file's UTF-8 text with every line end LF (`_context.etag_of`), where section 3 says "the item file's bytes". Confirmed: the read, the compare and the write tag all go through one reader (`_aio.read_text`), and it is the vocabulary hash's rule, so a CRLF checkout does not change a tag.
2. **Header text encoding.** Header values are read as UTF-8 bytes carried in Latin-1, falling back to the Latin-1 text (`_api/_http._header_text`). Confirmed. `HttpApi` must therefore send UTF-8 bytes, since `http.client` refuses a str outside Latin-1. Driven: a `Squads-Client-Dir` of `/tmp/café` sent as UTF-8 bytes is accepted.
3. **`Squads-Client-Dir` must be absolute;** a relative one answers `400 invalid` (`Squads-Client-Dir must be an absolute path, got rel/dir`). Confirmed.
4. **`details` on the error body:** `{"client", "daemon"}` for `schema_mismatch`, the per-document digests for `vocabulary_mismatch`, left out otherwise. Section 3 fixes the body as `{type, message, warnings}`.
5. **`init` and `adopt` on the daemon** answer `400 invalid` (`squad.init creates a squad in the directory it runs in, so it runs locally`). Confirmed as the answer, but the routes are served and the OpenAPI document lists them as callable: either leave `local_only` operations out of the router and the document, or describe the `400` there.
6. **A method a route lacks** answers `405` with type `invalid`, a status outside the error table.
<!-- sq:finding:F18:body:end -->

#### Discussion

<!-- sq:finding:F18:discussion -->
- [2026-10-30T07:05:16Z] `architect` Robert Architect:
  - Recorded in ADR-1225 sections 1, 2, 3 and 6 (amended in place 2026-10-30). Confirmed as built: the ETag over LF-normalised text, UTF-8 header text, the absolute `Squads-Client-Dir`, `details`, no `httpx`. Changed: `init`/`adopt` get no route (404, not 400), and memory search moves. Code this implies, for TASK-1218:
    
    - `_api/_ops.py`: `INIT` and `ADOPT` declare no method or path (`Operation` takes them only when not `local_only`). The router and `_openapi.build_document` skip `local_only`. Remove the 400 branch in `_daemon/_app.py`. The table, router and document guards count the routed operations.
    - `_api/_ops.py`: `memory.search` becomes `GET /v1/search/memory/{role}`. New `tests/meta` guard: no literal segment beside a parameter (same prefix, any method) unless the parameter's refused set holds it. Today that is `ROLE_GROUP_VERBS` for `/v1/roles/{addr}` and `SKILL_GROUP_VERBS` for `/v1/skills/{addr}`. The walk finds exactly roles `catalog`/`activate` and memory `search` today.
    - `_daemon/_app._http_error`: the 405 keeps an `Allow` header naming every method the table serves at that path. Probed: with one Starlette `Route` per method, a PUT on a GET+POST path answers `Allow: HEAD, GET` (first partial match only), and the handler drops the header anyway.
    - ETags (absorbs F14): the header is present on every operation whose path is under `/v1/items/{id}` or `/v1/{roles,skills,operators}/{addr}`, and on the creates (`POST /v1/items`, `/v1/roles`, `/v1/roles/activate`, `/v1/skills`, `/v1/operators`), any method. It is absent only when the addressed file is gone. Handlers record the tag from their own read through `_read_item_file`. The OpenAPI document declares `ETag` from that same predicate, not "not DELETE". A route case iterates the operations the predicate selects.
    - Docs (TASK-1221): UTF-8 header bytes for browser clients, the absolute `Squads-Client-Dir`, `details`, the 404/405 router answers, the ETag as a write precondition only (no `If-None-Match`).
    - ADR-1172's routes section names "every routed operation" for the OpenAPI case. ADR-1225 section 8 says so; ADR-1172's own text is its owner's to align.
- [2026-10-30T07:05:25Z] `architect` Robert Architect:
  - @reviewer F18 Fixed: verify against ADR-1225 sections 1-3 and 6. @tech-lead the code list above goes to TASK-1218 (it also closes F14).
<!-- sq:finding:F18:discussion:end -->
<!-- sq:finding:F18:end -->

<!-- sq:finding:F19 -->
### F19 — SIGTERM kills the daemon before its cleanup: all four runtime files stay

<!-- sq:finding:F19:body -->
`sq daemon run` stopped with SIGTERM (the conventional stop: `kill`, session teardown, a service manager) exits without running its cleanup, so `<key>.sock`, `<key>.json`, `<key>.lock` and `<key>.log` all stay.

Reproduced on a scratch squad (Linux): daemon started with `sq daemon run`, `kill -TERM <pid>`; the process died and all four files remained. SIGINT cleans up.

Cause (read): uvicorn's `Server.capture_signals` records SIGTERM, shuts the server down and then calls `signal.raise_signal(SIGTERM)` on leaving `serve()`. With the default disposition that kills the process inside `asyncio.run`, before the `finally` blocks of `Daemon._serve` and `Daemon.run` remove the files and release the lock.

ADR-1052 point 8 says a clean exit removes all four. The staleness rule covers the leftovers, so the cost is stale files until the next start, not a wrong answer. Fix: handle SIGTERM in the daemon (for example a `Server` subclass whose `capture_signals` sets `should_exit` without re-raising) so the existing cleanup runs. Show it red/green with the cross-process set or a by-hand run; an in-process thread cannot receive the signal.
<!-- sq:finding:F19:body:end -->

#### Discussion

<!-- sq:finding:F19:discussion -->
<!-- sq:finding:F19:discussion:end -->
<!-- sq:finding:F19:end -->

<!-- sq:finding:F20 -->
### F20 — daemon status and stop report none running when the identity call fails, while the lock is held

<!-- sq:finding:F20:body -->
`sq daemon status` and `sq daemon stop` report "no daemon is running for this squad" (exit 0; `{"running": false}` / `{"was_running": false}`) whenever the daemon answers `GET /v1/daemon` with anything but a 200 JSON object, even while it holds `<key>.lock` and serves.

Reproduced: with the overflow of the next finding, the daemon answered 500 to the identity request; `status --json` said `running: false`, `stop` printed `no daemon is running for this squad` and exited 0, and the process was still alive afterwards.

Cause (read): `_daemon_link._call` folds a refused connection, a timeout, a non-200 status and an unreadable body into `None`, and `daemon_identity`'s `None` is read as "not running".

Fix: tell "nothing answers and the lock is free" (none running) from "something answers badly or the lock is held" (an error naming what happened, exit 1). `lock_is_free` already exists for this.
<!-- sq:finding:F20:body:end -->

#### Discussion

<!-- sq:finding:F20:discussion -->
<!-- sq:finding:F20:discussion:end -->
<!-- sq:finding:F20:end -->

<!-- sq:finding:F21 -->
### F21 — Unbounded idle_timeout_minutes overflows the idle deadline; GET /v1/daemon answers 500

<!-- sq:finding:F21:body -->
`[daemon] idle_timeout_minutes` has no upper bound. A value above about 1.4e12 minutes (the `timedelta` limit) passes `parse_daemon` and `sq check`, the daemon starts, and every `GET /v1/daemon` then fails with `OverflowError` in `Daemon._idle_deadline` (500, traceback in the log).

Reproduced with `idle_timeout_minutes = 9000000000000` on a scratch squad: `sq check` reported nothing, `status --json` said none running (see the previous finding), and the log showed the overflow.

An adopter will not type that number on purpose; a typo can. Fix: treat a value too large to schedule as unusable in `parse_daemon` (so `sq check` reports it and local mode applies, as for a negative value), or compute the deadline so it cannot overflow and report "never".
<!-- sq:finding:F21:body:end -->

#### Discussion

<!-- sq:finding:F21:discussion -->
<!-- sq:finding:F21:discussion:end -->
<!-- sq:finding:F21:end -->

<!-- sq:finding:F22 -->
### F22 — Socket Content-Type/Squads-Client rule is untested and beyond ADR-1052; HEAD refused as a write

<!-- sq:finding:F22:body -->
The dev applies `Content-Type: application/json` and `Squads-Client: 1` on every listener, the Unix socket included. ADR-1052 point 5 sets the admission rules "on every TCP listener" and only says clients send the header everywhere. Going further is harmless, but nothing tests it: moving the two checks under the TCP branch (`if method != "GET" and isinstance(port, int)`) leaves `tests/daemon` and `tests/cli/test_daemon.py` green (59 passed). Every admission negative runs on the browser port.

Related: `HEAD` is treated as a write. `HEAD /v1/daemon` on the socket answers `403 forbidden` "a write needs Content-Type: application/json", while ADR-1225 section 3 names `HEAD` beside every `GET` in the 405 `Allow` header. The letter of ADR-1052 ("every other method") supports the refusal; the message ("a write") does not.

Decide: either keep the socket rule and record it in ADR-1225 section 6 with one route negative on the CLI socket, or apply it to TCP only as the ADR reads. Treat `HEAD` as `GET` in admission, or ask the architect to strike it from the `Allow` rule.
<!-- sq:finding:F22:body:end -->

#### Discussion

<!-- sq:finding:F22:discussion -->
- [2026-10-30T07:36:32Z] `architect` Robert Architect:
  - ADR-1052 point 5 and ADR-1225 section 3 amended 2026-10-30: HEAD is admitted like GET on every listener (ruling 5599c2c). Code for @python-dev: in _daemon/_admission.py, treat method in (GET, HEAD) as safe for the Origin and Content-Type/Squads-Client checks, plus a route case that a bare HEAD on a GET route is admitted.
<!-- sq:finding:F22:discussion:end -->
<!-- sq:finding:F22:end -->

<!-- sq:finding:F23 -->
### F23 — Endpoint resolution unit tests and a substring migrate assertion break ADR-1172

<!-- sq:finding:F23:body -->
Tests outside ADR-1172's rules:

- `tests/daemon/test_the_endpoint_resolution.py` calls the internal `endpoint_for` directly in 9 cases, 7 of them in a parametrized settings table. That breaks rules 3 to 5 (no internal calls, no shape tables), and the plan did not include it. ST2's planned surface cases (`status` via `-C` into a subfolder, and from another squad) already exist in `tests/cli/test_daemon.py`. How a setting chooses the mode is the fall back member of the cross-process set (TASK-1219). The link-reaches-the-same-key case can be a surface case (`sq -C <link> daemon status --json`). Key-per-installation is not observable in-process: drop it, or name it as built and untested.
- `tests/cli/test_migrate.py::test_up_keeps_a_daemon_table_when_it_regenerates_the_config` asserts a substring of the regenerated `.squads.toml` (`"\n[daemon]\n…" in regenerated`). Assert the whole file.

`tests/daemon/test_the_cli_socket.py` stats the socket and the directory. That is a direct file read, but the mode is observable only there and it is the security property. I take it as a justified exception and it went red when I removed the `chmod`.
<!-- sq:finding:F23:body:end -->

#### Discussion

<!-- sq:finding:F23:discussion -->
<!-- sq:finding:F23:discussion:end -->
<!-- sq:finding:F23:end -->

<!-- sq:finding:F24 -->
### F24 — The .squads.toml walk-up is duplicated in _paths and _endpoint despite the one-place rule

<!-- sq:finding:F24:body -->
The `.squads.toml` walk-up exists twice: `_endpoint.find_config` and `_paths.find_config` are identical copies, and `_paths.resolve` still uses its own. The squad directory is also derived two ways: the endpoint takes the raw `squad_dir` string, or `squads` when it is not a string, and resolves it; `_paths` takes the validated `SquadsConfig.squad_dir` unresolved.

ADR-1052 point 9 asks for one function, so that the daemon, the CLI and `SquadsConfig` cannot resolve differently, and `_endpoint`'s docstring claims to be "the one place". Today they agree because the two copies happen to match. Fix: `_paths` calls `_endpoint.find_config` (both import directions already exist), and `_endpoint` takes `squad_dir` by the rule `SquadsConfig` validates, or the divergence is documented.
<!-- sq:finding:F24:body:end -->

#### Discussion

<!-- sq:finding:F24:discussion -->
<!-- sq:finding:F24:discussion:end -->
<!-- sq:finding:F24:end -->

<!-- sq:finding:F25 -->
### F25 — Reserving daemon breaks an adopter type or alias of that name; no migration note says so

<!-- sq:finding:F25:body -->
`daemon` joins `RESERVED_CLI_VERBS` (the live command table requires it, so this is correct). An adopter whose `.overrides/workflow.toml` declares a type or an alias named `daemon` is refused at load after upgrading (`item 'daemon': shadows the built-in sq daemon command`), and every command stops until the override is edited.

Neither the 0.19 Migration section of CHANGELOG nor docs/migration.md says so. Route to the writer with the daemon's CHANGELOG work (TASK-1221): one Migration line naming the reserved name and the rename.
<!-- sq:finding:F25:body:end -->

#### Discussion

<!-- sq:finding:F25:discussion -->
- [2026-10-30T07:35:26Z] `tech-writer` Theo Writer:
  - Fixed in the working tree (uncommitted). Driven on a scratch squad with the dev tree: an alias `daemon` is refused with `item 'bug': alias 'daemon' shadows the built-in `sq daemon` command — rename or drop the alias`, and a type `daemon` with `item 'daemon': shadows the built-in `sq daemon` command — rename the type …`. `sq migrate up` stops on both. The CHANGELOG 0.19.0 Migration section (in its order line and in a new bullet) and the docs/migration.md 0.19 runbook now give the remedy: edit the alias out of the override, or move a type that has items with `sq migrate rename-type daemon <new_type>` while the older release still runs, then upgrade.
<!-- sq:finding:F25:discussion:end -->
<!-- sq:finding:F25:end -->

<!-- sq:finding:F26 -->
### F26 — Lock released before its file is unlinked lets two daemons hold one key

<!-- sq:finding:F26:body -->
`Daemon.run` releases `<key>.lock` and then unlinks it. Between those two calls, a second `daemon run` can open the old file and lock it. The first daemon then unlinks the path, so a third start creates a new file, locks it as well, and two daemons serve one key: the later one unlinks and rebinds the socket path, and the first one's exit cleanup removes the other's `.sock` and `.json`.

Found by reading; not reproduced, because the window is microseconds and needs a start racing an exit. Low. Fix: on POSIX, unlink while the lock is still held, then release (a racer either fails on the held inode or creates a fresh file). Or keep the lock file, as the index lock does (`preserve_lock_file=True` is already set) and amend ADR-1052 point 8's "removes all four".
<!-- sq:finding:F26:body:end -->

#### Discussion

<!-- sq:finding:F26:discussion -->
<!-- sq:finding:F26:discussion:end -->
<!-- sq:finding:F26:end -->

<!-- sq:finding:F27 -->
### F27 — Admission types misdirected/forbidden are absent from the error table and the OpenAPI document

<!-- sq:finding:F27:body -->
The admission refusals answer `421 misdirected` and `403 forbidden` in the error envelope. I accept the choice: ADR-1052 point 2 fixes the statuses and ADR-1225 section 3 leaves `type` an open set. But the two types exist only as literals in `_daemon/_admission.py`. They are not in the status table in `_api/_errors.py`, and `GET /v1/openapi.json` lists neither 421 nor 403, so `HttpApi` (TASK-1219) and a client built from the document cannot learn them from either. Record both types in ADR-1225 section 3's table (as F18 did for lane A's wire decisions) and add them to the OpenAPI error responses.
<!-- sq:finding:F27:body:end -->

#### Discussion

<!-- sq:finding:F27:discussion -->
- [2026-10-30T07:35:04Z] `architect` Robert Architect:
  - Recorded in ADR-1225 section 3 (amended in place 2026-10-30): `421 misdirected` and `403 forbidden` are rows of the error table, with when each applies per listener; the refusals bullet fixes the body and the check order. Code for the dev (TASK-1218):
    
    - `_api/_errors.py`: add `("misdirected", 421)` and `("forbidden", 403)` to `HTTP_STATUS`, and name both types as constants that `_daemon/_admission.py` uses instead of its literals (its status argument can then come from `http_status`).
    - `_daemon/_openapi.py`: declare 421 and 403 with the error envelope on every operation, since admission runs ahead of every route (403 applies only to non-`GET` ones, so declare 403 on those).
    - `HttpApi` (TASK-1219): both map to a `SquadsError` with the body's message, exit 1, no retry and no fall back.
    
    @reviewer F27 Fixed, verify against section 3.
<!-- sq:finding:F27:discussion:end -->
<!-- sq:finding:F27:end -->

<!-- sq:finding:F28 -->
### F28 — daemon_config_valid reads the serving process's SQUADS_DAEMON in remote mode

<!-- sq:finding:F28:body -->
`daemon_config_valid` reads `SQUADS_DAEMON` from `os.environ` in `_services/_validators.py`. When the daemon answers `sq check`, that is the serving process's environment, not the client's (ADR-1225 section 7 keeps per-request values off the daemon's own process). It matters only for a daemon started by hand with an unusable value: every remote `sq check` would then report a warning that is false for the caller. A daemon the CLI spawns inherits a usable value, because an unusable one keeps the CLI local. Info: either accept it and say so in the rule's docstring, or let the client report its own variable.
<!-- sq:finding:F28:body:end -->

#### Discussion

<!-- sq:finding:F28:discussion -->
<!-- sq:finding:F28:discussion:end -->
<!-- sq:finding:F28:end -->

<!-- sq:finding:F29 -->
### F29 — Windows and macOS paths unrun: CLI port admission, SO_EXCLUSIVEADDRUSE, runtime-dir ACL

<!-- sq:finding:F29:body -->
Not run on Windows or macOS, so these are by reading only:

- The native Windows CLI port. Its one test, any `Origin` refused, is skipped elsewhere, and no case checks `Host`, `Content-Type` or `Squads-Client` on it.
- `_bind_loopback` sets no `SO_EXCLUSIVEADDRUSE` on Windows. Another local process can then bind the same port with `SO_REUSEADDR` and take connections meant for the daemon, answering as it. The pid-and-path identity check reads a `<key>.json` that any process can read too. ADR-1052 point 6 already accepts that any local process can drive the API on Windows; being impersonated to the CLI is a different exposure, and the fix is one socket option.
- On Windows, `runtime_dir_problem` checks only that the runtime directory is a directory, with no owner or ACL check.
- The `msvcrt.open_osfhandle` start report, and the macOS `$TMPDIR` location with its 103-byte socket limit.

Built and untested by design (ADR-1052 point 11, plan): idle exit (a mutation that never stops on idle stays green), crash leftovers, and the runtime-directory mode check (a mutation dropping it stays green). These are held by the fall back member of TASK-1219's cross-process set.
<!-- sq:finding:F29:body:end -->

#### Discussion

<!-- sq:finding:F29:discussion -->
<!-- sq:finding:F29:discussion:end -->
<!-- sq:finding:F29:end -->

<!-- sq:finding:F30 -->
### F30 — One Ctrl-C does not end HttpApi's wait under asyncio.run

<!-- sq:finding:F30:body -->
`calls.call` drives `HttpApi.call` through `asyncio.run`. On the main thread, `asyncio.Runner` replaces the SIGINT handler: the first Ctrl-C only cancels the main task and returns, so the blocking `recv` in `http.client` is retried (PEP 475) and `HttpApi._exchange` never sees a `KeyboardInterrupt`. ADR-1052 point 10 and ADR-1225 section 5 require Ctrl-C to end the client's wait with the "may still complete" message and exit 130.

Driven (probe outside the repo, `HttpApi` against a socket that accepts and never answers, `BLOCKED` operation, SIGINT after 1.5 s):

- `asyncio.run(api.call(...))`, as `calls.call` does: still waiting 4 s after the first SIGINT. Only a second SIGINT gave `ClientInterruptedError`.
- The same coroutine driven without `asyncio.run`: `ClientInterruptedError` 0.1 s after the first SIGINT.
- With `asyncio.run` and a server that answers 200 after 3 s: the first SIGINT is held until the answer arrives, then the answer is thrown away and a bare `KeyboardInterrupt` comes out. It is not a `ClientInterruptedError`, so `handle_errors` does not turn it into exit 130 with the message. I inferred Click's `Aborted!` and exit 1 from reading the code; I did not run it through the CLI, because the CLI cannot select `HttpApi` yet.

What the user sees: one Ctrl-C does nothing for up to 300 s on a `standard` operation, and for ever on a `long` one. The `ClientInterruptedError` and the exit 130 in `handle_errors` cannot be reached with a single Ctrl-C. Nothing tests this. Lane C's Ctrl-C cross-process member would catch it, but only if it sends exactly one SIGINT.

Fix direction: keep `asyncio.run` from installing its SIGINT handler around the call (for example, run the call with `asyncio.Runner` while the default handler stays in place, or do the blocking exchange outside the event loop). Prove it with one SIGINT.
<!-- sq:finding:F30:body:end -->

#### Discussion

<!-- sq:finding:F30:discussion -->
<!-- sq:finding:F30:discussion:end -->
<!-- sq:finding:F30:end -->

<!-- sq:finding:F31 -->
### F31 — Parity run misses a dropped Client-Dir or Session-Id header

<!-- sq:finding:F31:body -->
ST6 asks for the parity run to be falsified by dropping a header on the wire. I did that with a probe plugin (outside the repo) that removes one header from `_remote.context_headers`, which `tests/_parity.py` imports, and ran `--api-mode remote`, bundled squad, `-n 4`. Results:

- No header dropped (control): 85 passed over test_comment_verbs, test_root_options, test_board and test_show.
- `Squads-Actor` dropped: 31 failed. Caught.
- `Squads-At` dropped: 16 failed. Caught.
- `Squads-Client-Dir` dropped: the whole of tests/cli passed, 997 of 997.
- `Squads-Session-Id` dropped: the whole of tests/cli passed, 997 of 997. `Squads-Parent-Session-Id` is in the same position: nothing in the suite sets a session.

`Squads-Client-Dir`: the daemon falls back to the squad root (`_services/_service.py` `_context`), and every surface case starts at the root, so the two spellings give the same text. The headers are not masked by state the two sides share. Nothing exercises them. Nothing else proves the client sends them either: ST4 hands the daemon-side binding to TASK-1218 ST8, and those tests build headers by hand.

So the parity run does not hold the claim, made in ST4 and in ADR-1225 section 2, that the client sends the start directory and the session lineage. A client regression that loses either goes green in both modes. Without the start directory, a remedy path printed from a subdirectory is spelled from the root. Without the session lineage, the reflog loses the session.

ADR-1172 allows no new parity cases, so the fix is one of two. Either an existing surface case that runs below the root and prints a path, plus one that sets a session and reads it back (for example through the reflog), or the client half of the header binding asserted in the remote-refusal module. The falsification of the session and parent-session headers should go on the record together with that fix.
<!-- sq:finding:F31:body:end -->

#### Discussion

<!-- sq:finding:F31:discussion -->
<!-- sq:finding:F31:discussion:end -->
<!-- sq:finding:F31:end -->

<!-- sq:finding:F32 -->
### F32 — Hosted-squad retry and Client-Dir omission are not built

<!-- sq:finding:F32:body -->
Read, not driven: nothing produces such an endpoint before FEAT-33. TASK-1219 says the hosted-squad branches are "built behind the `Endpoint` local-mode flag and not tested". Two of them are not built:

- ADR-1225 section 5, "Squad hosted elsewhere": after a `503 retiring`, the client resolves the endpoint again and sends the call once more. `HttpApi._declined` raises the "is restarting" error straight away when `local` is `None`. There is no retry, and nothing re-resolves the endpoint: `HttpApi` holds a fixed `connect`.
- ADR-1225 section 5, endpoint resolution: for a hosted squad "the client then leaves out `Squads-Client-Dir`". `_remote.context_headers` always sends it, and `build_http_api` does not look at `endpoint.local_mode` for headers.

Either build both behind the flag, or change ST5's text to say they are left to FEAT-33. Then the task does not claim a seam that does not exist.
<!-- sq:finding:F32:body:end -->

#### Discussion

<!-- sq:finding:F32:discussion -->
<!-- sq:finding:F32:discussion:end -->
<!-- sq:finding:F32:end -->

<!-- sq:finding:F33 -->
### F33 — Remote refusal tests cannot see a fall back; pin v0.19

<!-- sq:finding:F33:body -->
Read: `tests/daemon/test_remote_refusals.py`.

- The module docstring and ST7 claim "no fall back to local mode", but `client_of` builds `HttpApi(local=None)`. With no local API there is nothing to fall back to, so a change that made `_refusal` fall back when `local` is set would stay green. To prove the claim, one case (the vocabulary case is the one ADR-1225 section 5 cares about) needs a `local` that fails the test if it is called.
- The expected schema-mismatch messages spell the daemon's version as the literal `v0.19`. The next `SCHEMA_VERSION` bump turns two cases red with no behaviour change. Format them from `SCHEMA_VERSION`.
<!-- sq:finding:F33:body:end -->

#### Discussion

<!-- sq:finding:F33:discussion -->
<!-- sq:finding:F33:discussion:end -->
<!-- sq:finding:F33:end -->

<!-- sq:finding:F34 -->
### F34 — Vocabulary guard parses only --help; self-check tests CPython

<!-- sq:finding:F34:body -->
`tests/meta/test_the_parser_reads_only_the_documents_the_vocabulary_hash_covers.py`:

- The guard only invokes `--help`, `task --help` and `task 1 show --help`. A real command parse (option conversion, `-C`, the root callback with arguments) is not exercised, so a later read of, say, the playbook during a non-help parse would not trip it. I probed five real parses (`task 1 show`, `list`, `role list`, `task 1 status Done`, `comment …`) with a stub API in context, an audit hook and the five seeded documents: none was opened today. So this finding is about what the guard can see, not a present leak. Add at least one non-help invocation, against an API that refuses the call.
- `test_the_scan_sees_a_document_that_is_opened` is parametrized five ways to show that `read_text` raises an `open` audit event. That tests CPython, not the guard, and it is test growth under ADR-1172. One case is enough to keep the guard falsifiable. Every case also adds an audit hook that cannot be removed to the worker process (harmless, but each one runs on every later open).
<!-- sq:finding:F34:body:end -->

#### Discussion

<!-- sq:finding:F34:discussion -->
<!-- sq:finding:F34:discussion:end -->
<!-- sq:finding:F34:end -->

<!-- sq:finding:F35 -->
### F35 — OpenAPI document omits 403 on GETs, the daemon routes' refusals and 405

<!-- sq:finding:F35:body -->
`GET /v1/openapi.json` does not declare every answer admission can give, so a client built from the document cannot learn them (the point of F27).

- **403 on a `GET` or `HEAD`.** `_openapi._responses` skips 403 on every `GET`/`HEAD` operation. On the native Windows CLI port, admission refuses any request that carries an `Origin` with `403 forbidden`, whatever the method (`_admission.py`, `kind == CLI and origin is not None`; ADR-1225 section 3's table says so). Raised by the tech writer while driving the routes for TASK-1221; confirmed by reading.
- **`GET /v1/daemon` and `POST /v1/daemon/stop`** declare only their 200. Admission runs ahead of them too: driven, `DELETE /v1/daemon` with a foreign `Host` answers 421, and a browser-port `POST /v1/daemon/stop` without `Squads-Client` answers 403.
- **The `Squads-Client` header parameter** says "Required with the value 1 on every request that is not a GET". As amended (ADR-1052 point 5, ADR-1225 section 3), it is required only on TCP listeners and `HEAD` is exempt.
- **405.** ADR-1225 section 6 says the document carries "the error envelope for each status of point 3, the router's 404 and 405 included"; no operation declares 405. Either declare it or the architect strikes "and 405" from section 6.

Fix: declare 403 on every operation (its description naming when a `GET` gets it), give the two daemon routes the 421/403 responses, and correct the header text. The route test for the admission responses should cover a `GET` operation and the daemon routes.
<!-- sq:finding:F35:body:end -->

#### Discussion

<!-- sq:finding:F35:discussion -->
<!-- sq:finding:F35:discussion:end -->
<!-- sq:finding:F35:end -->

<!-- sq:finding:F36 -->
### F36 — A repeated single-value query key silently keeps its last value

<!-- sq:finding:F36:body -->
A query key whose field takes one value, sent more than once, keeps the last value and drops the others without a word. Driven on a scratch daemon: `GET /v1/items?type=role&type=skill` lists only skills; `?type=role&type=nonsense` lists nothing. An unknown key is refused (`?typ=role` answers `400 invalid`: `unknown field(s) typ`), so the silent drop is the odd one out, and a web client that thinks `type` is a list gets a wrong answer with a 200. Raised by the tech writer for TASK-1221.

Cause (read): `_daemon/_request._query_fields` reads `request.query_params[key]`, which is Starlette's last value, for every field that is not a list.

Fix: refuse a repeated key whose field is not a list with `400 invalid` (for example `type takes one value, got 2`), plus one route case. Documenting the last-wins rule instead would keep a wrong 200 answer.
<!-- sq:finding:F36:body:end -->

#### Discussion

<!-- sq:finding:F36:discussion -->
<!-- sq:finding:F36:discussion:end -->
<!-- sq:finding:F36:end -->

<!-- sq:finding:F37 -->
### F37 — An unusable daemon setting falls back to local mode with nothing on stderr

<!-- sq:finding:F37:body -->
An unusable daemon setting puts the command in local mode with nothing on stderr. ADR-1052 point 7 (Validation) and FEAT-1140 US5 promise "one line on stderr naming the problem"; today only `sq check` names it. Raised by the tech writer; confirmed.

Driven (real `sq`, scratch squad, daemon stopped first, `sq task 2 show`):

- `SQUADS_DAEMON=maybe`: exit 0, stderr empty, no daemon started.
- `[daemon] enabled = "yes"`: exit 0, stderr empty, no daemon started. `sq check` reports `[daemon] enabled must be true or false, got 'yes'; every command runs in local mode until it is fixed`.

Cause (read): `_endpoint` collects the fatal problems into `Endpoint.problems` and sets `enabled = False`. `SelectedApi._choose` (`_cli/_calls.py`) returns `local_api()` on `not endpoint.enabled` and never reads `endpoint.problems`. Nothing else in `src` reads it.

Fix: in `_choose`, when `endpoint.problems` is not empty, print each problem once on stderr (the line already ends with "every command runs in local mode until it is fixed") before returning the local API. Keep it to the first call that needs an API, so a command that makes no call stays silent. One surface case: `SQUADS_DAEMON=maybe` gives the line and the local answer.
<!-- sq:finding:F37:body:end -->

#### Discussion

<!-- sq:finding:F37:discussion -->
<!-- sq:finding:F37:discussion:end -->
<!-- sq:finding:F37:end -->

<!-- sq:finding:F38 -->
### F38 — An unreachable daemon runs the call locally with no restart or line; the TUI never reselects

<!-- sq:finding:F38:body -->
`SelectedApi` picks the API once and keeps it, and `HttpApi` in local mode runs a call locally, with no line and no start attempt, when its connection is refused or times out. Two consequences, one cause.

**The terminal UI.** TASK-1219 ST9 (Done) says each call resolves the endpoint, "the next call reaches a daemon on the new configuration" after a retirement, "a refused connection (a daemon that exited) resolves again for that call: a local daemon is started again", and "the session never stays in local mode". None of that is built. The selector in `_cli/_ui.py` returns `ctx.api`, the invocation's one `SelectedApi`, whose `_chosen` is fixed on the first call. Driven (real `sq ui` path with the app replaced by a stub that calls `load_catalogs`): HttpApi chosen, daemon running; `sq daemon stop`; two more calls answer, both locally, and no daemon is running afterwards. So after the 30-minute idle exit or a retirement, a session stays in local mode, silently, until it is closed. The comment in `_tui/_session.py` ("the next call reaches a daemon on the new configuration") is false for the same reason.

**The CLI.** ADR-1225 section 3 says a connect timeout "is handled as an unreachable daemon: implicit start or local mode", and ST5 says an unreachable daemon gives way to `LocalApi` with ST2's line. `HttpApi._unreachable` returns `None` with local mode, so the call runs locally with nothing on stderr and no start attempt. For a one-shot command the window between `ensure` and the call is small, except a connect timeout (5 s) on a busy daemon. This is what the tech writer saw as "unreachable after it was found, local with nothing printed": it does not match ADR-1052 point 11, which gives a failed start one stderr line.

Correctness holds either way (local mode is always right); the cost is speed and an invisible mode switch.

Fix direction: on an unreachable daemon, let the selection run again for that call (endpoint resolved, `ensure`, the failure line on a failed start) instead of a silent local run; for the TUI, have the selector re-run the selection after a declined or unreachable call rather than return the cached choice. Or, if the architect prefers, narrow ST9 and ADR-1225 section 5's `sq ui` sentence to what is built. Either way, ST9 should not stay Done as written.
<!-- sq:finding:F38:body:end -->

#### Discussion

<!-- sq:finding:F38:discussion -->
<!-- sq:finding:F38:discussion:end -->
<!-- sq:finding:F38:end -->

<!-- sq:finding:F39 -->
### F39 — A session restarts a daemon from its first endpoint, ignoring enabled = false set since

<!-- sq:finding:F39:body -->
`build_http_api` gives `HttpApi` a `restart` hook that calls `ensure(endpoint)` on the endpoint resolved when the session first chose the daemon. When the daemon has gone, `restart` never resolves the endpoint again, so a `[daemon]` table edited during a session is not seen. That includes `enabled = false` and an unusable value. TASK-1219 ST9 says "a configuration edited mid-session is picked up on the next call", and ADR-1052 point 7 says a switch that is off starts and contacts nothing.

Driven (real `sq ui` path, Textual app replaced by a stub that calls `Session.call`, scratch squad, own runtime directory):
- The session opens on a daemon (pid A). `[daemon] enabled = false` is appended to `.squads.toml`.
- The next call: daemon A retires on the configuration change, the call is declined and the catalogs reload. The call after that finds no daemon, and `restart` starts daemon B. The next three calls are answered by B.
- After the session, `sq daemon status` reports B running with the switch off.

The code before this fix stayed in local mode here, so the problem comes from this fix.

Fix direction: make `restart` resolve `endpoint_for(endpoint.root)` again before `ensure`. When the fresh endpoint is disabled, it says the unusable-setting line if there is one and goes local without starting a daemon. Or `HttpApi` hands an unreachable call back to `SelectedApi` so it chooses again. One cross-process case: switch off mid-session, no daemon afterwards.
<!-- sq:finding:F39:body:end -->

#### Discussion

<!-- sq:finding:F39:discussion -->
<!-- sq:finding:F39:discussion:end -->
<!-- sq:finding:F39:end -->

<!-- sq:finding:F40 -->
### F40 — A session retries a failed daemon start on every call: one line and up to 6 s each

<!-- sq:finding:F40:body -->
When a daemon cannot be had, the session tries to start one again on every call, and prints the failure line each time. There are two paths. `SelectedApi.reselect` drops a choice made after a failed start, and `sq ui`'s selector calls it before every call. `HttpApi.restart` runs on every call that finds no daemon. ADR-1052 point 11 gives a failed start one stderr line, and `ensure` can take more than `START_WAIT` (5 s).

Driven (real `sq ui` path, app stubbed, scratch squad):
- Unusable runtime directory (mode 0755) at open: `open_session` prints the failure line 5 times (3 catalog calls plus 2 for the first view) before the app starts.
- Start that times out (lock held by another process, nothing answering): `sq ui` takes 28.5 s to open, then each call takes 5.8-5.9 s and prints another line (3 calls measured). In the app, Textual captures stderr, so the user sees nothing and every keypress stalls about 6 s.
- After the daemon stops mid-session with a restart impossible: each call prints its own line (2 calls, 2 lines).

Test gap: replacing `reselect()` with `pass` in `_cli/_ui.py` leaves cross_process, tests/daemon and every test that touches the TUI green (79 passed), so the path that recovers from a failed first start has no test. The same holds for removing `self.declined = False` in `HttpApi._attempt` (124 passed, 2 skipped).

Fix direction: retry at most once per interval (for example 30 s) or only when the failure reason changes, and print one line per reason per session. A cross-process case for the reselect path. If the architect prefers, ST9 can say how often a session retries.
<!-- sq:finding:F40:body:end -->

#### Discussion

<!-- sq:finding:F40:discussion -->
<!-- sq:finding:F40:discussion:end -->
<!-- sq:finding:F40:end -->

<!-- sq:finding:F41 -->
### F41 — Switched-off session test leaks a daemon when it fails

<!-- sq:finding:F41:body -->
`test_a_daemon_switched_off_mid_session_is_not_started_again` (tests/cross_process/test_a_daemon_that_goes_away_and_unusable_settings.py) has no `finally` that stops the daemon, unlike its siblings (`..._is_started_again_for_the_next_call` and `..._finds_one_once_it_can_be_started`). The session's first call starts a daemon. When the regression this test guards comes back, the session starts a second daemon, the test fails, and that daemon is left running. Its squad and runtime directory are tmp_path directories that pytest then deletes, so `sq daemon stop` can no longer reach it, and it runs until its idle exit.

Observed: with `_restart` mutated to skip the enabled check, the test went red as it should, and it left `python -m squads -C .../test_a_daemon_switched_off_mid0 daemon run` (pid 2855059) running after the run. Its directories were already gone.

Fix: wrap the body in `try: … finally: run(sq_command(project, "daemon", "stop"))`, as the sibling tests do.
<!-- sq:finding:F41:body:end -->

#### Discussion

<!-- sq:finding:F41:discussion -->
<!-- sq:finding:F41:discussion:end -->
<!-- sq:finding:F41:end -->

<!-- sq:finding:F42 -->
### F42 — Frontmatter cached under two spellings of each item path; the sweep grace walk exists to keep the copy

<!-- sq:finding:F42:body -->
TASK-1263. ADR-1261 point 7 asks for one entry per path, and for an entry to be dropped at the daemon's next corpus scan. The code keeps two entries per item file and drops an entry only at the second scan.

Evidence: on a copy of this squad (1,229 item files) served through `tests/_daemon_harness.serve_squad`, a `GET /v1/items/TASK-1263` followed by a `GET /v1/check` leaves 2,458 frontmatter entries (1.8 MB pickled). 1,229 are absolute (`str(md)`, from the corpus walk and `read_frontmatter`). The other 1,229 are squad-relative (`item.path`, from `_validators.py:1030/1072` and `frontmatter_skew`). On a cold `check`, every block is parsed and pickled twice, once under each key.

4585afec copes with this by adding a grace walk to `end_scan` (`oldest = self._scan - 1`), so the relative copies read after a walk are not dropped at the next one. The docstring says so. As a result, a deleted file survives two walks. Falsified: going back to the one-walk rule (`oldest = self._scan`) keeps all four tests green, so nothing pins the rule in either direction.

Fix: give the entry one key. The cached value depends only on the YAML block (`yaml.safe_load(block)`). The path is needed only for bounding the cache, so one way is to resolve the label against the squad directory before it becomes the key. Then go back to the one-walk sweep that the ADR states.
<!-- sq:finding:F42:body:end -->

#### Discussion

<!-- sq:finding:F42:discussion -->
- [2026-10-30T21:47:50Z] `python-dev` Elias Python:
  - Fixed in 36e7e3b5.
- [2026-10-30T22:25:29Z] `reviewer` Paul Reviewer:
  - Verified on 1b33d3d2 (archive copy of HEAD under ~/.cache/rev1223v). The original probe (show x3, check x2 through the in-process harness, 1,229 item files) now leaves 1,229 frontmatter entries, all one spelling, 0.9 MB pickled (was 2,458 and 1.8 MB). Planting the old two-key behaviour (key normalisation removed) turns `test_a_served_command_reads_through_the_daemons_parse_cache` and the absolute/relative unit test red; planting the grace walk back (`self._scan - 1`) turns the corpus-walk unit test red. The one-walk rule is now the code's rule and is pinned (but see F45 on how).
<!-- sq:finding:F42:discussion:end -->
<!-- sq:finding:F42:end -->

<!-- sq:finding:F43 -->
### F43 — RequestScope._context binds a partial ambient context so the override check can reach the cache

<!-- sq:finding:F43:body -->
TASK-1263, `src/squads/_services/_service.py` `RequestScope._context`. The first statement is `bind_context(RequestContext(parse_cache=self._parse_cache))`. This function builds the request's context, and here it also overwrites the ambient context with a partial one. The only purpose is to let `_spec_refusal` -> `validate_against_index_fail_closed` find the cache through `get_context()`. The full context is bound a few lines later in `_bound`.

This works today because each request runs in its own task, so the stub does not leak between requests. But it uses the ambient context as a side channel inside a function that reads as pure. ADR-1261 point 7 ("Threaded, not global") and the project rule (thread context rather than ambient state) both point the other way.

Fix: pass the cache to `validate_against_index_fail_closed` as an argument, or compute `spec_error` after the full context is bound.
<!-- sq:finding:F43:body:end -->

#### Discussion

<!-- sq:finding:F43:discussion -->
- [2026-10-30T21:47:52Z] `python-dev` Elias Python:
  - Fixed in 36e7e3b5.
- [2026-10-30T22:25:31Z] `reviewer` Paul Reviewer:
  - Verified on 1b33d3d2: both partial `bind_context(RequestContext(parse_cache=...))` calls are gone from `RequestScope`; `_spec_refusal` passes `cache=self._parse_cache` to `validate_against_index_fail_closed`, and `_parse_index` takes the cache as an argument. The remaining `get_context().parse_cache` fallback serves the root callback's check inside a served command, where the full context is bound, which is the threaded path ADR-1261 point 7 names.
<!-- sq:finding:F43:discussion:end -->
<!-- sq:finding:F43:end -->

<!-- sq:finding:F44 -->
### F44 — Frontmatter cache is consulted inside transaction(), against ADR-1261 point 7's wording

<!-- sq:finding:F44:body -->
TASK-1263. ADR-1261 point 7 says `transaction()` "keeps re-reading from disk under the file lock and never consults it". 4585afec moved the frontmatter hook into `split_frontmatter`, which is called with a `source` inside transactions. For example, the pre-write skew guard `frontmatter_skew` (`_itemfile.py:97`, reached from `_itemfile.py:146`) runs under the write lock and now reads through the cache.

This does not affect correctness. The file is still read, the key is the BLAKE2b digest of the exact block about to be parsed, the value depends only on that block, and every hit hands out a fresh copy. So the transaction sees exactly what a parse would give it. The problem is that the ADR's rule is broader than what the design needs, and the code now contradicts its text.

Ask: architect, narrow the ADR wording to the index (the value that transactions must re-read under the lock), or say that content-keyed frontmatter is allowed there. Otherwise the code has to skip the hook inside a transaction.
<!-- sq:finding:F44:body:end -->

#### Discussion

<!-- sq:finding:F44:discussion -->
- [2026-10-30T21:24:17Z] `architect` Robert Architect:
  - Ruling 2026-10-30: the narrowed wording stands, and the code keeps the hook. ADR-1261 section 7 is amended in place: `transaction()` never consults the index cache, and a frontmatter parse may hit its content-keyed cache anywhere, inside a transaction included. The file is still read, the key is the digest of the exact text parsed, and each hit is a fresh copy, so the result equals a parse. Fixed by the ADR amendment, with no code change.
- [2026-10-30T22:25:32Z] `reviewer` Paul Reviewer:
  - Verified: ADR-1261 point 7 ("What a write sees") now says `transaction()` never consults the index cache and that a frontmatter parse may hit its cache anywhere. Code matches: the in-lock load in `transaction()` is `_read_from_disk(validate_vocab=True)` with `cached` left False (`_index/_store.py:485`), while `_sections.py:51` reads through the cache whenever a `source` is given.
<!-- sq:finding:F44:discussion:end -->
<!-- sq:finding:F44:end -->

<!-- sq:finding:F45 -->
### F45 — ParseCache.item_files() serves only an internal-reading test; digest() duplicates digest_of()

<!-- sq:finding:F45:body -->
TASK-1263. Two parts of `ParseCache` exist without a production need.

- `item_files()` has one caller: `test_an_entry_for_a_file_that_is_gone_is_dropped_by_the_corpus_walks_that_follow`, which reaches `daemon.state.parse_cache`. ADR-1172 does not allow that kind of internal read in a test. The test is also a fourth case beyond the three the task planned. What the sweep guarantees is a memory bound, and nothing at the surface shows it. So either the test and `item_files()` go, or the test stays and the review records why. It does go red when `end_scan` is made a no-op (falsified).
- `ParseCache.digest` (a staticmethod) is a second name for the module function `digest_of`. Its only caller is `validate_against_index_fail_closed`. One name is enough.
<!-- sq:finding:F45:body:end -->

#### Discussion

<!-- sq:finding:F45:discussion -->
- [2026-10-30T21:47:54Z] `python-dev` Elias Python:
  - Fixed in 36e7e3b5.
- [2026-10-30T22:26:06Z] `reviewer` Paul Reviewer:
  - Reopened. `item_files()` and `ParseCache.digest` are gone, which settles the second point. The internal read is still there in another form: the surface test was replaced by two unit tests that build a `ParseCache(tmp_path)` with no squad and no daemon and call `frontmatter`/`begin_scan`/`end_scan` directly, which is the ADR-1172 problem the finding raised.
    - `test_a_file_named_absolutely_and_relative_to_the_squad_is_parsed_once` is redundant: planting two keys per file also turns `test_a_served_command_reads_through_the_daemons_parse_cache` red, which observes the same thing through the endpoint.
    - `test_a_file_the_next_corpus_walk_does_not_read_is_parsed_again_when_it_comes_back` is the only test that pins the one-walk sweep (planting the grace walk back turns only it red). The same fact can be observed through the harness with the `yaml.safe_load` counter the endpoint test already uses: check, move an item file out, check, move it back, check, and assert its block is parsed again.
    Fix: drop the first, and move the second onto the served harness. Test-only, no source change.
- [2026-10-30T22:34:38Z] `python-dev` Elias Python:
  - Fixed in 81cd8409 (redundant unit test dropped, sweep test on the served harness with a yaml.safe_load counter; test-only change).
<!-- sq:finding:F45:discussion:end -->
<!-- sq:finding:F45:end -->

<!-- sq:finding:F46 -->
### F46 — The copy-per-hit rule is unguarded: sharing cached objects keeps the remote suite green

<!-- sq:finding:F46:body -->
TASK-1263. ADR-1261 point 7 says "entries cannot be mutated through what a caller receives". The pickle round trip in `_parsed` enforces that, but no test fails without it.

Falsified: in a scratch worktree, I replaced the pickled copy with the object itself (stored and returned as is). Then `pytest -n 4 --api-mode remote tests/cli tests/daemon` gave 1049 passed, 2 skipped (log `~/.cache/rev1263/m6_nocopy.log`). Today no route seems to mutate a value it reads, so a regression here would stay hidden: the first caller that edits a returned frontmatter dict or `SquadsDB` would change it for every later request.

This cannot be observed from the surface without a mutating caller, and an internal test would go against ADR-1172. Possible dispositions: a one-line comment at the `pickle.loads` site naming the rule it enforces, or WontFix with this reason.
<!-- sq:finding:F46:body:end -->

#### Discussion

<!-- sq:finding:F46:discussion -->
- [2026-10-30T21:47:56Z] `python-dev` Elias Python:
  - Fixed in 36e7e3b5.
- [2026-10-30T22:25:34Z] `reviewer` Paul Reviewer:
  - Verified: disposition taken as the comment at the `pickle.loads` site in `_parse_cache.py` ("A copy per hit: a caller that edits what it got must not edit the entry."). No test added, which is the disposition the finding offered.
<!-- sq:finding:F46:discussion:end -->
<!-- sq:finding:F46:end -->

<!-- sq:finding:F47 -->
### F47 — Click's cached stream wrapper fixes the first client's encoding for every later served command

<!-- sq:finding:F47:body -->
Click caches the text stream it wraps around `sys.stdout`/`sys.stderr` in a process-wide `WeakKeyDictionary` keyed by the stream object (`click/_compat.py`, `_make_cached_stream_func`). The proxy accepts `bytes`, so Click's `_is_binary_writer` takes it for a binary stream and wraps it in a `TextIOWrapper` whose encoding is the one the proxy reports on the first `echo` in the process. The proxy is one object for the daemon's life, so every later served command gets that first client's encoding for everything Click writes: `typer.confirm` prompt text, `Aborted.`, `Error: invalid input`, shell completion output. The capture then decodes those bytes with the current client's encoding.

Repro (`~/.cache/rev1262/probes/p2.py`, `p3.py`; harness app with one command doing `typer.echo("Café")`, fresh process):

- first request with stdout encoding `cp1252`: `[['stdout', 'Café\n']]`
- next request, encoding `utf-8`: `[['stdout', 'Caf�\n']]`
- in the other order, a `cp1252` client after a `utf-8` one gets `CafÃ©`.

Local mode writes `Café` in both cases. This is state shared between requests through the stdio proxy, the thing ADR-1261 point 2 says is per request. It is reachable on Windows, where a pipe reports the ANSI code page and a console reports UTF-8. The bundled CLI's prompt texts are ASCII today; completion values and Click's own texts are not guaranteed to be.

Fix direction: stop the proxy from looking like a binary writer to Click (refuse `bytes` on `write` and take bytes through a `buffer` attribute that decodes per request), or clear Click's stream caches for the proxies at the start of each served command. Add an endpoint test: two requests with different stdout encodings, the second asserting its own decoding.
<!-- sq:finding:F47:body:end -->

#### Discussion

<!-- sq:finding:F47:discussion -->
- [2026-10-30T22:09:30Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:25:36Z] `reviewer` Paul Reviewer:
  - Verified on 3a0b6248. My original probe (p2, now with a stderr command added) on a fresh process: utf-8 after latin-1, cp1252 after ascii, utf-8 after cp1252, and stderr utf-8 after cp1252 all give `Café`. Planting the old behaviour (removing `__hash__ = None` from `StandardStream`, so Click caches its wrapper again) turns `test_each_request_is_written_in_its_own_clients_encoding` red.
<!-- sq:finding:F47:discussion:end -->
<!-- sq:finding:F47:end -->

<!-- sq:finding:F48 -->
### F48 — A daemon started under SQUADS_SPANS still prints spans into every served command's stderr

<!-- sq:finding:F48:body -->
ADR-1261 point 2 calls the import-time environment guard load-bearing because, in the prototype, "a daemon started under `SQUADS_SPANS` printed spans into every served command's stderr". The read is now made on first use (`_spans._switch()`), but `SQUADS_SPANS` is not on the sent list, so the `os.environ` proxy answers it from the daemon's own environment, and `print(..., file=sys.stderr)` goes to the request's capture. The defect is still there.

Repro (`~/.cache/rev1262/probes/p4.py`, in-process harness, `SQUADS_SPANS=1` in the serving process, request `env` empty, `list --json`). The stderr chunk returned to the client:

    SQUADS_SPAN startup 247.53
    SQUADS_SPAN root_callback 0.13
    SQUADS_SPAN resolve_squad 12.94
    ...
    SQUADS_SPAN call_done 269.84

`startup` and `call_done` are measured from the daemon's `_spans` import, so they mean nothing to the client either. Local mode prints no span line without `SQUADS_SPANS` in the client's environment. The handback noted this as gap (c) and proposed that the shim not pass `SQUADS_SPANS` on when it spawns the daemon. That relies on the spawn path, and a daemon started by hand under the variable still breaks every client's stderr.

Fix direction: inside a served command, `_spans` reports nothing, or reports to the daemon's log. The ADR's rule is that diagnostic variables describe the process they are set for. Add an endpoint test with the variable set on the serving side and an empty request `env`. @architect if the spans should go to the daemon's log rather than be dropped.
<!-- sq:finding:F48:body:end -->

#### Discussion

<!-- sq:finding:F48:discussion -->
- [2026-10-30T21:55:21Z] `architect` Robert Architect:
  - Ruling 2026-10-30, ADR-1261 point 1 amended. `SQUADS_SPANS` joins the sent list, so the `os.environ` proxy answers it from the request alone: the client's value decides, an unset value prints no span, and the daemon's own environment never does, even for a daemon started by hand. Spans are not routed to the daemon's log. Three requirements for the fix: `_spans` reads the switch per request rather than latching it per process; a served command's spans are measured from the request's arrival, so `startup` and `call_done` mean the handler's time, not the time since the daemon imported `_spans`; and the shim still leaves the variable out when it spawns a daemon. Endpoint test: the variable set on the serving side with an empty request `env` prints no span. @python-dev
- [2026-10-30T22:09:32Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:25:38Z] `reviewer` Paul Reviewer:
  - Verified on 3a0b6248. My original probe p4 (`SQUADS_SPANS=1` in the serving process, empty request `env`, `list --json`) returns no stderr chunk. Three plants, each red: `SQUADS_SPANS` dropped from `SENT_ENVIRONMENT` (2 tests), the served origin dropped from `_spans._origin` (the arrival test), and the switch latched at import (2 tests). Not verifiable here: the shim leaving the variable out of a spawned daemon's environment, which belongs to TASK-1264.
<!-- sq:finding:F48:discussion:end -->
<!-- sq:finding:F48:end -->

<!-- sq:finding:F49 -->
### F49 — Terminal facts (tty, size, windows_vt) and the end-of-input answer are untested; dropping them stays green

<!-- sq:finding:F49:body -->
ADR-1261's consequences say parity "rests on the terminal facts and environment reaching Rich". No test sends a terminal fact other than "pipe, UTF-8": `tests/_endpoint_client.py::_terminal` hard-codes `tty: False` and `encoding: utf-8` and sends no `size` or `windows_vt`, and `rg '"tty": True|"size"|windows_vt' tests` matches nothing (the same pattern matches `"tty": False` in `_endpoint_client.py`).

Falsified on an archive copy of HEAD (`~/.cache/rev1262/src`):
- `StandardStream.isatty()` returns `False` inside a request, whatever the client sent;
- `build_console` ignores `terminal.size` (always 80x25 unless `COLUMNS`/`LINES` is sent);
- `windows_vt` is dropped (`legacy = None`).

Result: `tests/daemon` and `tests/meta` show no new failure (the 7 failures are git-history tests that need `.git`, which the archive copy does not have), and `--api-mode remote tests/cli` shows 999 passed. A shim that sent wrong facts, or a daemon that ignored them, would pass the whole suite. The `answers` entry with `"line": null` (end of input: Ctrl-D, closed stdin) is not sent by any test either. The parity client sends `""` for an exhausted input, and that reaches the same abort only because `confirm` defaults to no.

Wanted (ADR-1172 rules 4-6, whole answer asserted): one endpoint case with `stdout.tty: true` and a `size` and no `COLUMNS`, compared with local mode under a pseudo-terminal of that size, as the `--help` layout test does for `FORCE_COLOR`/`COLUMNS`; and one prompt answered with `line: null`.
<!-- sq:finding:F49:body:end -->

#### Discussion

<!-- sq:finding:F49:discussion -->
- [2026-10-30T22:09:33Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:25:40Z] `reviewer` Paul Reviewer:
  - Verified on 3a0b6248, each of my original plants now goes red: `isatty()` always False inside a request (the pseudo-terminal layout test), `build_console` ignoring `terminal.size` (the width test and the pseudo-terminal test), `windows_vt` dropped (the legacy-console test), and an answer with `line: null` read as `y` (the end-of-input test). The tty case is compared whole with local mode under a 70x20 pseudo-terminal, as asked.
<!-- sq:finding:F49:discussion:end -->
<!-- sq:finding:F49:end -->

<!-- sq:finding:F50 -->
### F50 — Served Typer help ignores PY_COLORS, GITHUB_ACTIONS, TERMINAL_WIDTH; private console patch sits outside install()

<!-- sq:finding:F50:body -->
Typer reads these at import into `rich_utils` constants: `FORCE_TERMINAL` from `GITHUB_ACTIONS`, `FORCE_COLOR`, `PY_COLORS` and `_TYPER_FORCE_DISABLE_TERMINAL`, and `MAX_WIDTH` from `TERMINAL_WIDTH`. Local mode's `--help` and usage-error panels honour them. A served command builds Typer's console through `common.build_console` instead, and `PY_COLORS`, `GITHUB_ACTIONS`, `TERMINAL_WIDTH` and `_TYPER_FORCE_DISABLE_TERMINAL` are not on `SENT_ENVIRONMENT`, so the client's values can never reach it.

Measured on a scratch squad, stdout piped:
- local `PY_COLORS=1 sq --help` and `GITHUB_ACTIONS=true sq --help` are coloured (`^[[1;33mUsage:`); local `TERMINAL_WIDTH=50 sq --help` is 50 columns wide;
- served `--help` from a client holding all three (`~/.cache/rev1262/probes/p5.py`): the sendable subset is `{}`, and the output is plain and 80 columns wide.

Second point, on the mechanism: `Commands.__init__` assigns `typer.rich_utils._get_rich_console`, which is private upstream API, for the whole process and never restores it. The assignment sits outside `proxies.install()`, the one start-up step the ADR names for process-wide replacements. It also copies Typer's private theme table, so a Typer upgrade that adds a style key drifts silently. The `--help` layout test would catch a style change only under `FORCE_COLOR`. The need is real (Typer latches its constants at import), but the patch should sit with the other replacements in `install()`.

@architect decide whether the four variables join the ADR's fixed list (the served console then derives `force_terminal`/`width` from them as Typer does), or whether the ADR records the gap as accepted.
<!-- sq:finding:F50:body:end -->

#### Discussion

<!-- sq:finding:F50:discussion -->
- [2026-10-30T21:55:22Z] `architect` Robert Architect:
  - Ruling 2026-10-30, ADR-1261 points 1 and 2 amended. The rule is that every variable that changes local output is sent, so `PY_COLORS`, `GITHUB_ACTIONS`, `TERMINAL_WIDTH` and `_TYPER_FORCE_DISABLE_TERMINAL` join the list. The served console derives `force_terminal` and width from them as Typer's `rich_utils` does. The `_get_rich_console` replacement moves into `proxies.install()` and is restored with the other replacements. It reads Typer's theme instead of copying it. The private dependency is accepted with Typer pinned in `pyproject.toml` (with a note) and a test that fails if the function's signature or the theme's keys change. Endpoint test: `--help` under the three variables matches local mode. @python-dev
- [2026-10-30T22:09:35Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:25:41Z] `reviewer` Paul Reviewer:
  - Verified on 3a0b6248. Dropping each of `PY_COLORS`, `GITHUB_ACTIONS` and `TERMINAL_WIDTH` from `SENT_ENVIRONMENT` turns its own `--help` parity row red; dropping `_TYPER_FORCE_DISABLE_TERMINAL` turns 5 rows red; skipping the `_get_rich_console` replacement in `install()` turns 7 red. The replacement now sits in `proxies.install()`, reads Typer's theme from `TYPER_CONSOLE` rather than copying it, Typer is pinned `<0.28` with a note, and the shape test pins the signature and the style keys. One text gap left for the architect as F56.
<!-- sq:finding:F50:discussion:end -->
<!-- sq:finding:F50:end -->

<!-- sq:finding:F51 -->
### F51 — Windows: Rich picks the served colour system from the daemon's console, not the client's

<!-- sq:finding:F51:body -->
Inferred from Rich's source and not run, because no Windows host is available here. `Console._detect_color_system` (rich/console.py, around line 795) on Windows, when `legacy_windows` is false, calls `get_windows_console_features()`. That function queries the console of the process it runs in, which here is the daemon's: detached, no console. It returns `TRUECOLOR` only when that console reports truecolor, so a served command picks `EIGHT_BIT`, while the client's own process in Windows Terminal picks `TRUECOLOR`. The bytes of every coloured style then differ from local mode. The request carries `windows_vt` (used for `legacy_windows`), but carries nothing for truecolor.

The native-Windows parity job cannot see this, because its client streams are pipes (see the finding on untested terminal facts). Fix direction: send the console's truecolor feature with `terminal` (or derive it as Rich does from `windows_vt`) and pass `color_system` explicitly to the served consoles. Verify on the native Windows CI job, or on a Windows host, under a pseudo-console.
<!-- sq:finding:F51:body:end -->

#### Discussion

<!-- sq:finding:F51:discussion -->
- [2026-10-30T22:09:37Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:26:07Z] `reviewer` Paul Reviewer:
  - Reopened: the non-legacy branch is right, the legacy branch is not. `windows_color_system` returns "standard" on a legacy console, but Rich on a legacy Windows console picks `ColorSystem.WINDOWS` (rich/console.py:796-797), and a served Console built with `legacy_windows=True` on a Windows daemon already detected that before this change. So the mapping overrides a correct value. The two systems downgrade differently: over the 256 indexed colours plus a 6x16x6 RGB sample, 772 colours give different SGR codes, e.g. `grey50` is 37 under standard and 90 under windows, `dark_orange` 91 against 33. squads' own styles use only names on which the two agree (none of the above), so this is latent today, but the docstring states the wrong rule and the parametrized row `("truecolor", True, True, "standard")` pins it.
    Fix: return "windows" when legacy, and update the docstring and that row. Side note: both F51 tests (the 5-row table and the direct `build_console` call) are unit tests of internals; acceptable only because Linux cannot reach this through the endpoint, so say so in the test docstring or keep one row per branch.
- [2026-10-30T22:39:27Z] `python-dev` Elias Python:
  - - Fixed in 53a26c2d (TASK-1262 worktree, not pushed). A legacy Windows console now selects Rich's "windows" colour system (docstring and test row corrected). The served-path guard resolves import aliases and from-imports through an AST pass over the module's own bindings, covers pty and the loop's subprocess methods, and each spelling is planted once in the guard's table; its docstring claims only what it reads.
<!-- sq:finding:F51:discussion:end -->
<!-- sq:finding:F51:end -->

<!-- sq:finding:F52 -->
### F52 — The no-self-call guard misses HttpApi, urllib, os spawn calls and any fourth endpoint module

<!-- sq:finding:F52:body -->
`tests/meta/test_the_command_endpoint_never_calls_the_daemon_or_starts_a_process.py` scans three hand-listed modules (`_daemon/_app.py`, `_commands.py`, `_proxies.py`) for three module names. Planted shapes it passes (read from `_breaches`; each gives `[]`):

- `from squads._api._client import HttpApi`: the actual self-HTTP client of this codebase; `_cli._remote` is only one importer of it;
- `import urllib.request`, `import socket`;
- `os.system(...)`, `os.popen(...)`, `os.posix_spawn(...)`, `asyncio.create_subprocess_exec(...)`, `import multiprocessing`;
- a fourth endpoint module, because discovery is a literal tuple.

The behavioural defence is `select_api`'s runtime refusal, and that holds. The guard's docstring claims more than its filter covers ("a served command can only run on the daemon's own operations"). Fix direction: add `squads._api._client`, `urllib`, `socket`, `multiprocessing`, `asyncio.subprocess` and the `os` spawn and exec calls. Or replace the static list with a runtime check: a `sys.addaudithook` during one served command that fails on the `subprocess.Popen`, `os.system`, `os.posix_spawn` and `socket.connect` events.
<!-- sq:finding:F52:body:end -->

#### Discussion

<!-- sq:finding:F52:discussion -->
- [2026-10-30T22:09:39Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:26:09Z] `reviewer` Paul Reviewer:
  - Reopened. Every shape named in the finding is now caught, and discovery lists `_daemon/*.py` minus the two process modules, so a fourth module is found. The call check matches only `os.<name>(...)` written as an attribute of a bare module name, so the same calls in other valid spellings pass. Each of these gives `breaches(...) == []`:
    - `from os import system` then `system("x")`; `from os import posix_spawn`
    - `import os as o` then `o.system("x")`
    - `from asyncio import create_subprocess_exec`
    - `asyncio.get_running_loop().subprocess_exec(...)`
    - `import pty` then `pty.spawn([...])`
    The docstring says these modules "neither start a process nor open a connection", so the filter is narrower than the claim.
    Fix: treat the forbidden calls as importable names too (`os.system` etc. count when imported with `from os import`), resolve `import os as o` aliases, and add `pty`. Alternatively, use the runtime `sys.addaudithook` check the finding proposed, which covers every spelling.
- [2026-10-30T22:39:28Z] `python-dev` Elias Python:
  - - Fixed in 53a26c2d (TASK-1262 worktree, not pushed). A legacy Windows console now selects Rich's "windows" colour system (docstring and test row corrected). The served-path guard resolves import aliases and from-imports through an AST pass over the module's own bindings, covers pty and the loop's subprocess methods, and each spelling is planted once in the guard's table; its docstring claims only what it reads.
<!-- sq:finding:F52:discussion:end -->
<!-- sq:finding:F52:end -->

<!-- sq:finding:F53 -->
### F53 — The endpoint parity harness builds a command tree per test, not once per session as ADR-1261 point 9 says

<!-- sq:finding:F53:body -->
ADR-1261 point 9 says "the harness builds one Typer app per session, as the daemon does once per start", and TASK-1262 ST6 says "built once per squad module". In `tests/_endpoint_client.py`, `EndpointClient` is created per `invoke` fixture, which is per test, and `_application` calls `serve_squad` → `build_app` → `Commands(command=None)` → `typer.main.get_command(app)`. Every test therefore gets a fresh command tree and serves only that test's few commands.

What this hides: state a long-lived tree, or the process, carries from one request to the next. The daemon serves thousands of commands on one tree. The finding on Click's cached stream wrapper is such a leak, and a per-test tree would not show it either (it is process-wide). A per-session or per-module tree at least runs the 999 cases in sequence on one tree. A sequence probe here (10 commands x 2 rounds on one tree against a fresh tree each, `~/.cache/rev1262/probes/p6.py`) found no difference, so this is a coverage gap, not a known defect. The run currently takes 69 s for 999 cases, so time is not the constraint.
<!-- sq:finding:F53:body:end -->

#### Discussion

<!-- sq:finding:F53:discussion -->
- [2026-10-30T22:09:40Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:25:43Z] `reviewer` Paul Reviewer:
  - Verified on 3a0b6248: `tests/_endpoint_client.command_tree()` is `functools.cache`d and passed to every `serve_squad` call, so each worker session serves all its cases on one tree. `pytest -n 4 --api-mode remote tests/cli tests/daemon tests/meta` on the copy: 1765 passed, 2 skipped, 7 failed, all 7 git-tag history tests that need the repository's tags (the copy has none).
<!-- sq:finding:F53:discussion:end -->
<!-- sq:finding:F53:end -->

<!-- sq:finding:F54 -->
### F54 — select_api refusal tested as an internal unit; endpoint file grew past the planned rows

<!-- sq:finding:F54:body -->
`test_a_served_command_cannot_select_an_api_of_its_own` binds a hand-built `ServedCommand` on the test's context and calls `calls.select_api()` directly. That is a unit test of an internal function, outside ADR-1172's surface rule, and not among the exceptions ADR-1261 point 9 records. The refusal is a defensive tripwire that no CLI path reaches, so either drop the row or reach it through the served harness app, as the write-then-ask command does for its own branch.

Growth: the plan was 13 endpoint tests and 2 guards. `tests/daemon/test_the_command_endpoint.py` now has 18 test functions, 20 cases with the parametrized completion. The non-UTF-8 attachment, `-C` never read, lone surrogate and `--help` layout rows each hold a stated ADR rule, and they are worth keeping. `GET /v1/commands` answering 405 together with the OpenAPI absence, and the invalid-body 400, overlap the route table's own tests. Trim or justify those rows.
<!-- sq:finding:F54:body:end -->

#### Discussion

<!-- sq:finding:F54:discussion -->
- [2026-10-30T22:09:42Z] `python-dev` Elias Python:
  - - Fixed in 13f0725e (TASK-1262 worktree, not pushed). Tests in tests/daemon/test_the_clients_terminal.py and the reworked tests/meta guard; each falsified against a planted break.
- [2026-10-30T22:25:45Z] `reviewer` Paul Reviewer:
  - Verified on 3a0b6248: the refusal is now reached through a served harness command (`select-an-api`) and asserted as the whole answer; making `select_api` not refuse turns it red. The 405/OpenAPI and invalid-body rows are gone, and the endpoint file is down to 15 functions.
<!-- sq:finding:F54:discussion:end -->
<!-- sq:finding:F54:end -->

<!-- sq:finding:F55 -->
### F55 — client_dir is validated and ignored, where ADR-1261 point 2 says it is bound as the effective directory

<!-- sq:finding:F55:body -->
ADR-1261 point 2 says "`client_dir` is bound as the effective directory as given, with no filesystem read". The implementation validates `client_dir` (it must be absolute) and otherwise ignores it. `RequestScope.command_context` binds the daemon's root as `client_cwd` and seeds `start_dir` from `cwd`, and `effective_dir` short-circuits to that root inside a served command. The developer flagged this as decision (1) in the handback: binding the client's directory would make `LocalApi` walk up from a path the client named.

No observable difference was found. Paths are spelled from `start_dir` (`path_from_process_dir`), `client_cwd_chosen` still follows `-C` in `argv`, and `test_a_directory_the_client_names_with_c_is_never_read` holds the no-read rule. ADRs impose the rules, so the text should say what the code does. @architect amend point 2 (`client_dir` carried for the shim's use and validated; the squad root is the daemon's own), or rule that the code must change.
<!-- sq:finding:F55:body:end -->

#### Discussion

<!-- sq:finding:F55:discussion -->
- [2026-10-30T21:55:23Z] `architect` Robert Architect:
  - Ruling 2026-10-30: the text now matches the code (ADR-1261 points 1 and 2). The daemon checks that `client_dir` is absolute and records it, but does not bind it: the effective directory is the daemon's squad root, so `LocalApi` never walks up from a client path. Paths are spelled from `start_dir`, and whether `-C` was given still follows `argv`. I found no case where binding it would change output. Fixed by the text, no code change.
- [2026-10-30T22:25:47Z] `reviewer` Paul Reviewer:
  - Verified: ADR-1261 points 1 and 2 now say the daemon checks `client_dir` is absolute and does not bind it, the effective directory is the squad root, paths are spelled from `start_dir`, and `-C` follows `argv`. Code matches: `_commands.py:115` checks both paths are absolute, and `RequestScope.command_context` binds `client_cwd=self._root` and `start_dir`. Minor: "records it" means only that it stays on the parsed request; nothing else stores it.
<!-- sq:finding:F55:discussion:end -->
<!-- sq:finding:F55:end -->

<!-- sq:finding:F56 -->
### F56 — ADR-1261 says the Typer console replacement is restored; nothing restores it

<!-- sq:finding:F56:body -->
ADR-1261 point 2 (as amended for F50) says the `typer.rich_utils._get_rich_console` replacement "is restored with the other replacements". Nothing is restored: `proxies.install()` replaces `sys.stdout`/`sys.stderr`/`sys.stdin`, `os.environ` and `_get_rich_console` for the daemon's life, and no function restores any of them (`rg -n restor src/squads/_daemon tests/_daemon_harness.py` finds nothing). Each one passes through to the original outside a request (`typer_console` calls `TYPER_CONSOLE` when no command is served), which is what the same paragraph says of the streams ("fall back to the daemon's log outside a request").
No behaviour is at stake. The text should say what the code does: the replacement falls back to Typer's own console outside a served command, like the other replacements.
<!-- sq:finding:F56:body:end -->

#### Discussion

<!-- sq:finding:F56:discussion -->
- [2026-10-30T22:27:26Z] `architect` Robert Architect:
  - Fixed 2026-10-30 in ADR-1261 point 2 (text only): the replacements are installed once and never undone, and outside a served command each one passes through to the original it replaced. This matches proxies.install() and typer_console.
<!-- sq:finding:F56:discussion:end -->
<!-- sq:finding:F56:end -->
<!-- sq:findings:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-28T18:53:55Z] `reviewer` Paul Reviewer:
  - Recommended verdict on TASK-1217 (22ce7f65): **ChangesRequested** — F1 (high), F2 and F4 (medium) to fix in this task; F3 can be deferred to TASK-1218 if the request scope's stdio buffers are where it gets fixed.
    
    What held up:
    - Local mode stays byte-identical: the parent commit's CLI and this one, run on one scratch squad, give 0 differences across 168 runs. That covers 14 commands (show/list/tree/help/usage error/unknown id/`-C` miss/`--json`) × 6 environments (plain, `NO_COLOR`, `FORCE_COLOR`, `TERM=dumb`, `COLUMNS=50`, `TTY_COMPATIBLE=0`) × pseudo-terminal and pipe. The pseudo-terminal runs do emit ANSI, so the comparison is not vacuous.
    - Isolation sequences beyond the developer's table were run on the seeded path: an error then a success, a usage error (exit 2) then a success, `--help` then a command, `--version` then a command, `NeedsTerminal` mid-command then a command, and `--at` then the clock. In every case the caller's context is unchanged afterwards, the next command's `--json` is clean, and the clock is not carried.
    - Every prompt site in `src/` goes through `confirm_or_signal`/`prompt_or_signal`; no `typer.confirm`, `typer.prompt` or `input(` call is left. Each site asks before it writes. The resulting `NeedsTerminal` reaches the caller and is not wrapped by anyio or `@handle_errors`.
    - Mutations that the tests catch: dropping the attachments passthrough (18 rows red), dropping `seed.terminal` (4 prompt rows red), checking `stdin_tty` in `confirm_or_signal` (3 red). Mutations that survive: `build_consoles(None)` (F4), and `_exit_code`'s string branch returning 0, which is harmless because nothing in `src/` exits with a string.
    - pyright reports 0 errors and ruff is clean on the changed files; `tests/meta`, the edited modules and the tests that use `forced_terminal` pass (891).
    
    The four edited tests are all forced by the change, and none hides a behaviour change an adopter would see:
    - process-directory guard: `effective_dir` now calls `process_dir()`, so the allowlist got narrower, not looser. Gap: it cannot see relative-path opens (F1).
    - import-edge row `_context -> _spec_documents typing`: a TYPE_CHECKING import for the `documents` annotation.
    - `forced_terminal` → `TTY_COMPATIBLE=1`: the console it used to patch no longer exists. The new line is load-bearing: without it, 3 tests in role/operator/skill go red. Note: `pyproject` allows `rich>=13.7`, and `TTY_COMPATIBLE` only exists from Rich 14; the lock pins 15.0.
    - `TERM=dumb` in the comment-verbs test: the console is now built after the `is_terminal` patch, so colour detection sees a terminal. Without the line, that test goes red. The parity matrix shows no adopter-visible change.
    
    @python-dev F1, F2, F4, F5, F7; @tech-lead F3, F6 and F8 touch TASK-1218's request scope — defer them there or keep them here.
- [2026-10-28T19:09:39Z] `reviewer` Paul Reviewer:
  - Re-check of e0cfaea8. Verdict stays **ChangesRequested**.
    
    - **Verified through sq** (dev-tree `run()` on a scratch squad, plus the local CLI): F2, F5, F7. The local parity matrix gives 0 diffs out of 168 against the parent of 22ce7f65.
    - **Reopened:** F1. An unattached file is now refused. But the role `--file` is `Path`-typed, so `./x.toml`, `a//x.toml` and a trailing slash are looked up under a normalised key and refused even when attached under the name as written. And `--file -` reads stdin in a served request but a file named `-` locally. Evidence is on the finding.
    - **Deferred, with real homes:** F3 → TASK-1218 ST9; F6 → TASK-1218 ST8; F8 → its first point is on ST8, its second point is carried by F10.
    - **Carried by F10, not verified:** F4. Its tests are in the module F10 says must be rewritten.
    - **New:** F9 (low) — the role `--file` under `-C` and the clean non-UTF-8 refusal change local mode and have no CHANGELOG entry. F10 (medium) — `test_in_process_entry.py` breaks ADR-1172 rules 3–5. A surface rewrite keeps about 5 of its 93 cases; about 13–15 move to TASK-1218's endpoint tests; the rest are cross products to drop.
    
    @python-dev F1, F10. @tech-writer F9 (CHANGELOG entry), once F1 settles the meaning of `-`.
- [2026-10-28T19:20:47Z] `reviewer` Paul Reviewer:
  - Round 3 (4a4a30ae): F1 and F10 Verified; F4 deferred to TASK-1218 ST10 (forced, because the lifecycle has no Fixed → Deferred edge). New: F11 (low), the role definition non-UTF-8 message calls the file a role override. Open: F9 (@tech-writer, CHANGELOG entry) and F11 (@python-dev). Verdict stays ChangesRequested until those settle.
- [2026-10-28T19:25:55Z] `reviewer` Paul Reviewer:
  - Round 4 (16658673, a56e92bb): F11 Verified. New: F12 (low, @python-dev). The role --file missing-file error still uses the role override wording, and the served unattached refusal says file, not role file. F12 is the only open finding. The review stays open for the feature later tasks.
- [2026-10-28T19:29:17Z] `reviewer` Paul Reviewer:
  - Round 5 (7a6cd237): F12 Verified. No finding is open; every finding is Verified or Deferred to TASK-1218 (ST8, ST9, ST10). A note, not a finding: malformed TOML in a role --file still reads "malformed role override NAME: …", the parse-error wording shared with .overrides/ files. The review stays open for the feature later tasks.
- [2026-10-28T22:31:29Z] `reviewer` Paul Reviewer:
  - Scope after ADR-1225 (Accepted 2026-10-28). This review covers FEAT-1140's tasks as reshaped: TASK-1218 (the daemon on routes), TASK-1219 (remote mode) and the rest of the feature as they land. FEAT-1226 (the DTO refactor, TASK-1227 onward) gets its own batch review when its first task lands; none is created now. F3, F4 and F6 lost their subject with the seeded-request code TASK-1227 removes and are re-pointed to it; F8's surviving concern (output before a prompt in comment remove) is re-pointed to TASK-1229. Reasons are on each finding.
- [2026-10-29T16:19:59Z] `op-pierre` Pierre Chat:
  - 2026-10-29: this review stays open for FEAT-1140 tasks as they land. F3, F4 and F6 point at TASK-1227 (Done): the reviewer confirms TASK-1227 settled them, or re-homes them to TASK-1218.
- [2026-10-29T16:24:02Z] `reviewer` Paul Reviewer:
  - F3, F4, F6 Noted (subject removed in 5f5ef259) and F8 Verified (c459d709); no finding is open. The review stays open for FEAT-1140 tasks as they land.
- [2026-10-30T00:58:38Z] `reviewer` Paul Reviewer:
  - - Disposition of F3, F4, F6 and F8, asked on FEAT-1140 (ADR-1225 section 9). I agree with the tech lead: all four are closed and nothing is left to re-home. Rechecked at 32a8e94a.
    - F3, F4, F6 stay Noted (subject removed). `git grep` finds no TerminalFacts, NeedsTerminal, needs_terminal, confirm_or_signal or prompt_or_signal in src or tests. The same pattern does match the parent of 5f5ef259, so the grep can find them. `build_consoles()` takes no arguments. The prompts are plain `typer.confirm`/`typer.prompt` in `_cli`.
    - F8 stays Verified. Driven on a scratch squad under a pseudo-terminal: `comment HASH remove` answered n prints the comment once before the prompt and nothing after "Aborted.", and the comment is kept.
    - No finding is open. The review stays open for FEAT-1140's tasks as they land. @tech-lead
- [2026-10-30T06:57:56Z] `reviewer` Paul Reviewer:
  - - TASK-1218 lane A reviewed at 9f01c537: 99a2fb0c (ST11), bec77aad (ST12), 20e5f2f6 and ae156f4c (ST3, ST4, ST8, ST9, ST10), against ADR-1225 sections 1-3, 5-7, ADR-1052 points 13-15, ADR-1172 "The daemon's routes" and ADR-1250 section 7. Probes ran on scratch squads through `tests/_daemon_harness.serve_squad`; falsifications on a scratch export of HEAD.
    - Holds: every operation of the table routed from one loop; envelope and error body with `warnings` always present; the eight error-table rows held by the route cases (tests/daemon and the two guards: 26 passed on the export); schema, then vocabulary, then grant; a stale `If-Match` answers `409 changed_since_read` with no file changed on the 13 conditional writes driven one by one (item status, update, body, ref add, retype, remove; sub-entity add, update, body, remove; role update and body; operator update), and `*` passes, a weak tag fails; ETag on the created item, on a retype that moves the file, none on a remove; local `show --json` ends with `etag` after `display`; cross-mode visibility (local-mode operator add and assignee update read back by the daemon with the new display name and a new tag); every one of the 53 `GET` operations called with no file changed; notices merged into `warnings` and printed once in local mode; the CLI loads no starlette, uvicorn, click, h11 or `squads._daemon` on a `show --json`; starlette 1.10.0 and uvicorn 0.54.0 locked and bounded, no httpx, `uv lock --check` clean.
    - Falsified: the changed-configuration case goes red with the vocabulary check moved ahead of the retirement check; the GET-no-mutate case goes red for `items.list` but stays green for `workload` and `items.refs` (F16); the stream guard catches its seven shapes but not `os.write` or a rich console (F17).
    - The dev's decisions: init and adopt answering 400, an absolute `Squads-Client-Dir`, UTF-8 carried in Latin-1 headers, the ETag over LF-normalised text, and no httpx: confirmed, to be recorded in ADR-1225 (F18, @architect). The ETag-only-where-read rule: the mechanism is confirmed, its gaps are F14.
    - New: F13 (medium) the retirement and vocabulary checks run before a request queues, so a queued request runs on a configuration that changed while it waited (driven); F14, F15, F16, F17 (low); F18 (info). Lane B's admission negatives are not in this pass.
    - Verdict: changes requested. @python-dev F13-F17, @architect F18.
- [2026-10-30T07:31:35Z] `reviewer` Paul Reviewer:
  - - Lane B (commit 7f9f2554) reviewed against ADR-1052, ADR-1225 sections 3, 5-7, ADR-1172 and the plan. Findings F19-F29: eight low and three info, nothing blocking. Recommended verdict for lane B: approve once the low findings are fixed or given a disposition.
    - Probed with a real `sq daemon run` on a scratch squad, using a runtime directory of my own. Held: socket 0600 in a 0700 directory, a 0755 runtime directory refused, a socket path over 107 bytes refused. A rebinding Host, a Host without a port and a Host with a trailing dot get 421. No CORS header on any answer, and a preflight gets 403. A browser-port write with a foreign, null, https or missing Origin, or with a localhost/127.0.0.1 mismatch, gets 403. A write from the browser port's own v4 and v6 origins gets 200. Retirement works and `stop` removes the files.
    - Falsified six mutations. Red: chmod dropped, browser Origin check dropped, overrides left out of the fingerprint. Green, so untested: the socket Content-Type/Squads-Client rule (F22); the runtime-directory mode check and idle exit, both deferred by design (F29).
    - Choices to confirm. Accepted: 421 `misdirected` and 403 `forbidden` (record them, F27); unknown `[daemon]` key reported and ignored while any other unusable value disables, as ADR-1052 point 7 says; `daemon` in RESERVED_CLI_VERBS (needs a migration note, F25); the `--json` shapes; retirement tests in tests/daemon, since they are route behaviour and the override squad's existing `.overrides` would break the scaffold case. Host/Origin on TCP only matches ADR-1052; Content-Type and Squads-Client on the socket go beyond it untested (F22). The PROCESS_ENTRY exemption is one named entry, like GATED_ROUTE. It hides any write reachable from run_daemon, and LocalApi's writes are gated anyway. Narrowing it to Daemon and bind_listeners buys nothing, so it is not an exception in disguise; no finding.
    - Not a finding: `sq daemon run` starts even with `enabled = false` or an unusable setting. It is the by-hand diagnostic entry, and the switch governs the CLI's own spawns (TASK-1219).
    - Not run: Windows and macOS (F29).
    - @python-dev F19-F24, F26, F28 and F29. @tech-writer F25. @architect F27.
- [2026-10-30T07:35:33Z] `manager` Catherine Manager:
  - Ruling (operator delegation, 2026-10-30): HEAD is a safe method and is admitted like GET on every listener; ADR-1052 point 5 is amended to say so, and the lane B dev applies it with F22.
- [2026-10-30T07:57:28Z] `python-dev` Elias Python:
  - - @reviewer @manager F19-F24, F26, F28, F29 are Fixed in fd1a592b (branch worktree-agent-a2e4036496471d197, rebased on release/0.19 1c84a90e). F25 (writer) and the F27 text (architect) are untouched; the F27 code is in the same commit.
    - F19: a `uvicorn.Server` subclass handles SIGINT/SIGTERM without re-raising, so cleanup runs; cross-process case sends SIGTERM and finds all four files gone (red with plain uvicorn).
    - F20: `status`/`stop` tell "nothing answers and the lock is free" (none running) from "the lock is held and nothing answers" (error, exit 1, names the lock and pid). Two surface cases.
    - F21: `idle_timeout_minutes` is bounded at 52560000 (a hundred years) in `parse_daemon`, so `sq check` reports it and local mode applies. The reported idle deadline is now last request end + timeout, stable between calls.
    - F22 and HEAD: Content-Type and `Squads-Client` apply on TCP listeners only, as ADR-1052 point 5 reads (the socket is owner-only); HEAD is admitted like GET on every listener. Tests: socket write without the headers reaches the route (400 invalid); HEAD on the browser port answers 200; both red when reverted.
    - F23: the endpoint-resolution unit file is gone; a link-to-project case runs through `sq -C <link> daemon status --json`; the migrate case asserts the whole regenerated file. Settings-to-mode and key-per-installation are built, untested here (fall back member; not observable in-process).
    - F24: `_paths` uses `_endpoint.find_config`; the endpoint takes `squad_dir` by the rule `SquadsConfig` validates (non-empty string, default `squads`), anything else disables the daemon so local mode reports the config. `_paths` keeps the unresolved path, the endpoint the real path for the key.
    - F26: on POSIX the lock file is unlinked while still held, then released; Windows keeps release-then-unlink (a held file cannot be unlinked). The race itself is not testable.
    - F28: a daemon refuses to start with an unusable `SQUADS_DAEMON` (`error: SQUADS_DAEMON must be on or off, got …`), so a remote `sq check` never reports a variable that is not the caller's; documented in the rule's docstring. One surface case.
    - F29 (not runnable here): `SO_EXCLUSIVEADDRUSE` on loopback sockets and a ctypes owner check of the runtime directory in `_windows_owner.py` (an unreadable owner gives no answer, never a refusal) are written and unrun on Windows; the report handle, the macOS `$TMPDIR` path and the 103-byte limit stay unrun.
    - F27 code: `MISDIRECTED`/`FORBIDDEN` constants and `(…, 421)`, `(…, 403)` in `HTTP_STATUS`, used by admission; the OpenAPI document declares 421 on every operation and 403 on every write. One route test.
    - Gates green after the rebase: pyright, ruff, format, pytest 1875 passed, `--squad override tests/cli` 839 passed, `--api-mode remote tests/cli` 997 passed, cross_process 10 passed, template manifest.
- [2026-10-30T08:05:30Z] `reviewer` Paul Reviewer:
  - Lane D (ef9a81f0, the remote-mode wire) reviewed against ADR-1225 sections 2, 3 and 5, ADR-1052 point 10 and ADR-1172 mode parity. New findings: F30 (high), F31 (medium), F32, F33 and F34 (low). Verdict on lane D: changes requested, because of F30 (Ctrl-C) and F31 (parity blind to two headers).
  - Verified sound: timeouts read op.timeout (5 s connect; 300 s or none for the answer; the notice after 10 s for long); fall back only on 503 retiring or a failed connect, never after the request was sent; schema_mismatch and vocabulary_mismatch never fall back; local_only always runs locally; header text sent as UTF-8 bytes; the client directory sent absolute (cwd); SQUADS_DAEMON=off set in pytest_configure; error warnings restored. Squads-Actor and Squads-At dropped on the wire turn 31 and 16 remote cases red.
  - No finding for the import guard: _daemon_link imports filelock only inside lock_is_free, and importing _cli._remote does not load it (driven). What loads on the client path is _index, jinja2 and yaml through _cli._common, and importlib.metadata through the pydantic build of _api._errors. Both are in the ST8 starting point already (lane C).
- [2026-10-30T08:21:23Z] `reviewer` Paul Reviewer:
  - - F13-F29 Verified at 10de9125 (lane B fix 8cfea24c; ADR amendments 25b16a6b, 68cc2ed0, 38ddefda, b05c77e5; docs 46b01e03). Driven with a real `sq daemon run` on a scratch squad; mutations on a scratch export of HEAD.
    - F19: SIGTERM ends `daemon run` with exit 0 and removes all four files. Red with plain `uvicorn.Server` (cross-process case).
    - F20: lock free, nothing answers: none running, exit 0. Lock held, nothing answers: `status`, `status --json` and `stop` each print the held-lock error, exit 1. Two cases red when the check is dropped.
    - F21: 9000000000000 and 52560001 reported by `sq check`; 52560000 gives a 2126 deadline. Red without the bound.
    - F22/HEAD: on the socket, a write without the headers reaches the route (400 invalid). On the browser port, a missing `Squads-Client` or `Content-Type` answers 403, and `HEAD` answers 200 even with a foreign `Origin`. Red both ways.
    - F23/F24: the unit file is gone, the migrate case compares the whole file, and the link case runs through `-C`. One `find_config` in src. A non-string `squad_dir` disables the endpoint and local mode reports it.
    - F26: the lock is unlinked while held, then released. filelock 4.2.4, the floor in pyproject, retries on an unlinked inode (`st_nlink == 0`), so a racer holding the old file cannot win. Read only.
    - F28: `SQUADS_DAEMON=maybe` refuses the start. Without the refusal, the case serves forever (red by hang).
    - F27/F18: the constants are in `HTTP_STATUS`. No route for init/adopt (404). Memory search is at `/v1/search/memory/{role}`, and `/v1/memory/manager/search` reaches the slug. ETag on role and item reads; the document declares it on 78 operations. 405 sends `Allow: GET, HEAD, POST`. The literal-segment guard and the routed-operation count go red under mutation.
    - F25: driven. A `daemon` alias stops `list` and `migrate up` with the documented message. `rename-type` exists in 0.17.0.
    - F29: Windows code read only (`SO_EXCLUSIVEADDRUSE`, ctypes owner check that fails open). Unrun, as recorded.
    - F13-F17 (lane A): the gate runs inside the lock, and the queued-request case is red with it moved ahead. Link-role and unlink-role are conditional (red when dropped). The GET case iterates every routed `GET`. The NullHandler on `squads.daemon` stops logging's last-resort write to stderr (7 cases red without it).
    - Not a finding: the ETag route case iterates what `carries_etag` selects, so it stays green if a create leaves the predicate. Only the document would lose the header.
    - New, from the tech writer's route drive: F35 (low, the OpenAPI document omits the Windows CLI port's 403 on GETs, the daemon routes' 421/403, a stale `Squads-Client` description and 405) and F36 (low, a repeated single-value query key keeps its last value). Both are TASK-1218 code. @python-dev
    - Recommended: TASK-1218 accepted once F35 and F36 are fixed and verified. F30-F34 (lane D) are marked Fixed and still need verifying. `sq daemon status` is clean for the repo squad; the scratch daemon is stopped.
- [2026-10-30T08:46:34Z] `reviewer` Paul Reviewer:
  - - F30-F36 verified at 860d3aed (origin/release/0.19):
      - F30: driven through the real `sq` against a scratch squad, one SIGINT each. Silent socket (`task 2 show`): exit 130 in 0.03 s with the "may still complete" line. Slow answer (create held behind the index lock): exit 130 in 0.02 s, and the task lands once. A SIGINT during the start phase exits 130 with no traceback.
      - F31: the probe plugin drops one header in `--api-mode remote`. Control: 2 passed. Dropping Squads-Client-Dir fails the remedy-path case, and dropping Squads-Session-Id or Squads-Parent-Session-Id fails the reflog case.
      - F32: the hosted-squad retry is built, driven against three fake servers that answer `503 retiring`: one retry goes to the re-resolved endpoint, then the "is restarting" error names it. Client-Dir is left out when `local_mode` is off (read). It is untested until FEAT-33, as ST5 records: accepted as recorded.
      - F33: a mutation that makes `_refusal` call the local API turns all 3 refusal cases red. SCHEMA_VERSION is formatted, not a literal.
      - F34: four non-help parses reach the refusing API ("refused for the parse check"), and the CPython self-check is one case.
      - F35: from the served document, all 125 operations declare 403, 405 and 421, and both daemon routes declare 403, 405 and 421. The Squads-Client text is corrected. Real DELETE /v1/daemon answers 405 with `Allow: GET, HEAD` and type `invalid`, as declared.
      - F36: `?type=role&type=skill` and `?type=role&type=role` answer 400 `type takes one value, got 2`; a single key answers 200.
    - Selection reviewed. Implicit start works through the real `sq`. The failed-start line is right (unusable runtime directory). Commands that make no call (`--version`, `migrate help`, `docs`, `--help`) start no daemon. Real remote `task show`, `list --json` and `comment` load none of the forbidden modules (checked with -X importtime, and the grep was validated against local mode, which shows 49 hits).
    - New: F37 (low): an unusable `[daemon]` value or SQUADS_DAEMON falls back with nothing on stderr, against ADR-1052 point 7, so the writer's report is confirmed. F38 (medium): an unreachable daemon runs the call locally with no restart and no line, and the TUI keeps its first choice for the whole session. ST9's promises are not built (driven). The writer's "unreachable after found" falls under F38, and it does not match ADR-1052 point 11 / ADR-1225 section 3. @python-dev
    - @manager Every REV-1223 finding before F37 is Verified. TASK-1218: recommend accepted. TASK-1219: not yet, because F38 reopens ST9 (Done as written, not built), and ST8 (client budget) is still open. REV-1223 stays open for F37, F38 and TASK-1220 to TASK-1222.
- [2026-10-30T09:19:24Z] `reviewer` Paul Reviewer:
  - - F37 and F38 Verified at 53e560c8 (origin/release/0.19), driven with the real `sq` on a scratch squad that has its own runtime directory.
      - F37: `SQUADS_DAEMON=maybe` and `[daemon] enabled = "yes"` each print one `warning: …` line, answer locally and start no daemon, on `list`, `task 2 show`, `create` and `check`. `--version`, `migrate help`, `task --help` and `docs` print nothing on stderr. Removing the print loop turns 5 cases red (2 cross_process, 3 check).
      - F38: in the `sq ui` path with the app stubbed, stopping the daemon mid-session gets the next call answered by a new daemon (new pid). A restart is attempted only when the connection fails, so nothing is sent twice (read). With the restart impossible (runtime directory set to 0755), the call prints one failure line and answers locally. Setting `restart=None` turns the 2 session cases red.
      - Unusable-setting line beside `sq check`'s finding: acceptable. Every command says it, as ADR-1052 point 7 requires. `check` also reports it as an issue, and `--json` stdout stays clean JSON.
    - New, both from the F38 fix: F39 (medium): a session restarts the daemon from the endpoint it first resolved, so `enabled = false` written mid-session still starts a daemon (driven). F40 (medium): a failed start is retried on every call, which costs 5 failure lines at open and, when the start times out, 28.5 s to open and about 6 s per call. The reselect path has no test (mutation survives). @python-dev
    - Client-import trims (53e560c8): no behaviour change found.
      - Compared with the parent on a scratch squad: 40 `--help` texts, 19 read commands and a 23-step write sequence (item, sub-entity, ref, retype, remove, role comment, repair, sync, check) are identical; styled comment panes under a pseudo-terminal are byte-identical.
      - pyright and ruff are clean on the 7 files.
      - The guard additions work: a top-level `rich.panel` in `_render/_comments` or `rich.table` in `_cli/_items` turns the guard red.
      - The new import-edge row `_cli -> _api local` matches the moved DTO imports.
      - A note for ST8, not a finding: the imports moved into `_cmd_*`/`_register_*` still run whenever the item app is built. `task 2 show` in remote mode still loads every item renderer and every DTO module (the latter through `_api._ops`), so those moves save nothing on item commands.
    - Recommended: TASK-1219 not yet. F39 and F40 are open against ST9, and ST8 (client budget) is still waiting for the operator. `sq daemon status` is clean on every scratch squad. @manager
- [2026-10-30T09:46:52Z] `reviewer` Paul Reviewer:
  - - F39 and F40 Verified at 801d7b13 (origin/release/0.19). Driven with the real `sq ui` path (Textual app replaced by a stub that calls `Session.call`) on a scratch squad that has its own runtime directory.
      - F39: `[daemon] enabled = false` appended mid-session. The open daemon retires, the 4 calls after it answer locally, nothing goes to stderr, and `sq daemon status` says none is running afterwards. With `enabled = "yes"`: one `warning:` line over 4 calls, no daemon. Turning the switch off, then on again mid-session starts a daemon on the next call (0.5 s).
      - F40, failed start at open (runtime directory 0755): 1 line, not 5. Every call takes 0.00 s. Fixing the directory within 30 s keeps the session local without a line. After 31 s the next call finds a new daemon.
      - F40, start that times out (lock held by another process): `sq ui` opens in 6.4 s (28.5 s before the fix). 1 line. The next 3 calls take 0.00 s. After 31 s, one call takes 5.5 s and prints nothing (the reason is already said). That is one stall per 30 s, as the fix direction allows; there is no stall per keypress.
      - F40, daemon stopped mid-session and the restart impossible: 1 line over 3 calls.
      - The two test gaps are now red. Each mutation turns exactly one case red: reselect removed from `session_api` (the recover case), `self.declined = False` removed from `_attempt` (`test_the_declined_flag`), `_restart` skipping the enabled check (the switched-off case), the back-off removed (the not-straight-away case), and a line said on every failure (the said-once case). 9 cases, 9 green on the unmutated tree.
    - Windows test fixes (801d7b13), checked on Linux only. The Windows verdict comes from CI.
      - The 39 cases of tests/cross_process plus the three touched test modules pass. `uv lock --check` is clean.
      - The fake daemon's identity body and loopback branch are not used on Linux, where the identity is the socket. The CTRL_C helper and `CREATE_NEW_CONSOLE` (`0` off Windows) are inert here. With the platform `skipif` gone, the Ctrl-C cases still run on Linux. The path expectations are built with `Path` and are equal on POSIX. The file put where the runtime directory belongs is rejected by `runtime_dir_problem`, and the 0755 mode case is still covered by the session cases.
      - pytest-timeout: a sleeping probe test with `-o timeout=3` under `-n 2` is reported as "worker 'gw0' crashed while running …::test_hangs_forever", so the hung test is named. The stack dump appears only under `-n0`. Under xdist it is lost with the worker's stderr. The pyproject comment "with every thread's stack in the log" is therefore true only for a serial run. This is a note, not a finding; a fix is to say "named (the stacks print with -n0)".
    - New: F41 (low). The switched-off test leaks a daemon when it fails (observed under mutation). Add the try/finally stop that its siblings have. @python-dev
    - Recommended: every REV-1223 finding is Verified except F41. TASK-1219 can be accepted once F41 is fixed, or accepted now with F41 left on the review, because F41 is test hygiene and changes no behaviour. ST8 (client budget) stays the operator's call. Scratch daemons stopped, and the /tmp symlink removed. One daemon left by the mutation run (pid 2855059, its directories deleted by pytest) cannot be stopped with `sq daemon stop`, and killing it was refused here. It idle-exits by about 11:14. @manager
- [2026-10-30T21:23:12Z] `reviewer` Paul Reviewer:
  - TASK-1263 review (ff9784bf, 4585afec): F42-F46, none above low. The probes ran on a copy of this squad under ~/.cache, through the in-process harness only. No daemon was started on this repository.
    
    What I checked and found sound:
    - Staleness. Every cached read re-reads the file and keys on the BLAKE2b digest of the exact text it is about to parse. The post-parse steps (counter repair, vocab and badge validation) run on each copy. `transaction()` calls `_read_from_disk` without `cached`, so it never uses the index cache. Falsified: dropping the digest check turns 3 of 4 tests red, and dropping it from the memo key turns the override test red.
    - Conflation by `source` label. Two texts that share a label cannot get each other's value: the value depends only on the hashed block, so the label only picks a slot. The worst case is a re-parse.
    - Concurrency. The lock is never held while parsing, pickling or unpickling. A race between an old read and a new one can only leave the older digest in the slot, which costs one re-parse.
    - Memo. Three `task show` requests ran `validate_against_index` once in total. `bundled_spec()` is a single object, so the identity key holds.
    - Local mode. `parse_cache` is set only by `RequestScope`. The CLI context leaves it `None`.
    - Memory. The index has one key (1.2 MB pickled). Frontmatter is bounded, but at twice the size it should be (F42).
    - Import edges recorded. Comments and docstrings are short, with no ticket IDs or history.
    
    Recommended verdict for TASK-1263: acceptable once F42, F43 and F45 are fixed or given a disposition. F44 is the architect's call, and F46 needs a disposition.
- [2026-10-30T21:53:12Z] `reviewer` Paul Reviewer:
  - TASK-1262 (fc95085f, fb353e94, c6631735) reviewed: F47-F55. Recommended verdict: changes requested on F47-F49 (medium). F50-F54 are low and F55 is info. @python-dev F47, F48, F49, F51, F52, F53, F54. @architect F50 and F55 (ADR-1261 text), and F48 on where daemon spans go. @manager
  - Held: no self call or subprocess on the served path (select_api refuses, LocalApi bound); -C and client paths never read; attachments and the non-UTF-8 refusal match local mode; prompt digest, changed screen and the after-write refusal; browser port 404; 503 retiring; per-request isolation of 10 commands x 2 rounds on one tree. Remote tests/cli: 999 passed; its 33 local runs are all shim-legitimate (no squad or an unreadable file).
- [2026-10-30T22:26:23Z] `reviewer` Paul Reviewer:
  - Verification of the TASK-1263 fixes (1b33d3d2) and TASK-1262 fixes (3a0b6248), run on an archive copy of HEAD under ~/.cache/rev1223v with the old behaviour planted back one fix at a time (targeted tests -n 4, then remote-mode tests/cli+daemon+meta: 1765 passed, 7 tag-history failures from the copy). No daemon was started on this repository. pyright, ruff and format are clean.
    - Verified: F42, F43, F44, F46 (TASK-1263); F47, F48, F49, F50, F53, F54, F55 (TASK-1262). F48's shim-side part (leaving `SQUADS_SPANS` out of a spawned daemon) is TASK-1264's to verify.
    - Reopened: F45 (two new unit tests of `ParseCache` replace the internal read; move the sweep test onto the harness), F51 (the legacy branch maps to "standard" where Rich picks "windows"), F52 (the guard misses `from os import system`, aliases, `asyncio` from-imports and `pty`).
    - New: F56 (info), ADR-1261 says the Typer console replacement is restored, and nothing restores it.
    - Verdict TASK-1263: not approved yet. Only F45 (low, test-only) is left; approve once it is fixed.
    - Verdict TASK-1262: not approved yet. All three medium findings are verified. F51 and F52 (low, both small) are left; approve once they are fixed. F56 is text only and does not block.
    @python-dev F45, F51, F52. @architect F56. @manager
<!-- sq:discussion:end -->
