---
id: ADR-1261
sequence_id: 1261
type: decision
title: 'The CLI''s remote mode: a shim and a private command endpoint'
status: Accepted
author: architect
refs:
- FEAT-1140
- ADR-1052
- ADR-1224
- ADR-1225
- ADR-1172
- TASK-1219
description: The CLI becomes a stdlib shim that sends argv to a private daemon endpoint,
  which runs the CLI in process on LocalApi and renders; local fallback before sending;
  content-keyed parse cache
created_at: '2026-10-30T19:12:57Z'
updated_at: '2026-10-30T20:35:40Z'
---
<!-- sq:body -->
## Context

The operator set a new direction for the CLI's remote mode on 2026-10-30 (FEAT-1140, comment c2dced7), after the daemon benchmark recorded on TASK-1219 (comment 64fd727). Under ADR-1224 and ADR-1225 the CLI in remote mode parses, calls one route through `HttpApi` and renders in its own process. Measured:

1. **The client is the cost.** Installed 0.19.0, 15 interleaved runs, copy of this repository's squad: `task show` 689 ms local against 686 ms through the daemon; the best case, `list --json`, 662 against 507 ms (1.3x). The remote client spends about 236 ms importing `squads._cli` before it sends anything (`_cli._calls` 183 ms, `_cli._common` 101 ms); the daemon's handler for `task show` takes 65-120 ms. After splitting `_api/_ops.py`, the client overhead of `task show` is a median 311-337 ms against a 275/235 ms budget (TASK-1219, comment ee453fe). The bare interpreter starts in 13 ms (ADR-1225, section 5).
2. **The daemon keeps no squad data between requests** (ADR-1052, point 12), so corpus-wide work gains nothing: `check` takes 7.3 s locally and 7.1 s through the daemon.
3. **Where a read spends its time** (manager, 2026-10-30, this repository's squad): parsing `.squads.json` costs about 30 ms per command; YAML-parsing the frontmatter of 1,317 item files about 985 ms, of which reading their raw text is 23 ms. Frontmatter is about 1 s of `check`'s 7 s. Reads take no lock: `IndexStore.load` reads without one and relies on the atomic `os.replace` commit; `transaction()` re-reads from disk under the file lock and uses no snapshot.
4. **Hashing what is read is cheap** (measured 2026-10-30, this repository, three runs): reading and BLAKE2b-hashing every `.md` under `squads/` (1,317 files, 17.6 MB) took 39-59 ms; `os.stat` of the same files 2-6 ms; reading and hashing the 2.1 MB index 5-7 ms.
5. **TASK-1217 built and TASK-1227 removed an in-process entry** (commit 22ce7f65, ADR-1225 section 9): `run(argv)`, consoles per invocation, `start_dir`, `documents`, attachments served through `read_client_text`, terminal facts and the `NeedsTerminal` signal. `run`, the consoles, `start_dir`, `documents` and `_paths.process_dir()` remain. The CLI reads client files in two places only: `--file` (one shared option helper, `-` meaning stdin) and `import`'s `FILE` argument, all through `read_client_text`.
6. **Prompts.** Two sites remain under the CLI: `confirm` in `_cli/_common.py` (item, sub-entity and comment removal; under `--json` it asks on stderr and reads a line from stdin) and `init`'s name prompt. Every prompting command asks before it writes (ADR-1052, 2026-10-28 ruling; ADR-1224 point 1: a prompt sits between two calls, never inside one).
7. **Process state the CLI touches.** Consoles resolve through the request context. `--json` goes through `print()`, and Click's prompts and echo write to `sys.stdout`/`sys.stderr` directly. Rich reads `NO_COLOR`, `FORCE_COLOR`, `COLUMNS`, `TERM` and related variables from `os.environ` unless handed `_environ`. `actor.session_from_env()` reads `os.environ`. Module-level state in `_cli` is limited to CODE caches by the mutable-state guard; Click keeps its context stack per thread. `call()` runs an async `Api` through `asyncio.run`, which cannot run on a thread that already runs an event loop.

## Decision

### 1. One private command endpoint

`POST /v1/commands` takes a command line and answers with its output. It is served **on the CLI listener only** (the Unix socket on POSIX, the CLI port on Windows), never on the browser port. It is private to one installation: the shim and the daemon always come from the same package (ADR-1052, point 8), so it carries no version negotiation, is absent from `GET /v1/openapi.json`, and `docs/api.md` says only that the CLI reaches the daemon through a private channel outside the API, with no wire format. The admission rules of ADR-1052, point 5, apply to it.

**Request** (UTF-8 JSON):

- `argv`: the arguments after `sq`, as JSON strings; undecodable POSIX bytes travel as lone surrogates and round-trip.
- `cwd`: the client's absolute process directory, which spells paths in messages.
- `client_dir`: the absolute directory the `-C` values resolve to from `cwd` (equal to `cwd` without `-C`). The shim resolves it, as it must to find this daemon (point 4), and reads attachments against it. A `-C` the shim cannot resolve makes it run the command locally, so the refusal is local mode's own. `-C` stays in `argv` and the served command does not apply it again.
- `env`: the values of a fixed list, absent ones left out: `SQUADS_SESSION_ID`, `SQUADS_PARENT_SESSION_ID`, `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR_FORCE`, `TTY_COMPATIBLE`, `TTY_INTERACTIVE`, `COLUMNS`, `LINES`, `TERM`, `COLORTERM`, and the shell-completion variables of bash, zsh and fish: `_SQ_COMPLETE`, `_SQUADS_COMPLETE`, `COMP_WORDS`, `COMP_CWORD`, `_TYPER_COMPLETE_ARGS`, `_TYPER_COMPLETE_WORD_TO_COMPLETE`, `_TYPER_COMPLETE_FISH_ACTION`. The list is one literal in the shim's module; a variable outside it does not exist for a served command. The daemon's diagnostic variables, `SQUADS_SPANS` and `SQUADS_DAEMON`, are never on it: they describe the process they are set for, so the shim prints its own spans and the daemon's handler time (sent back with the answer) under `SQUADS_SPANS`.
- `prog_name`: the name the client was invoked as (`sq` or `squads`). Typer derives the usage text and the completion variable from it.
- `terminal`: for each of stdin, stdout and stderr, whether it is a terminal and its encoding; the terminal's size; on Windows, whether the console has virtual-terminal processing on.
- `attachments`: client files the command line names (point 3).
- `answers`: the user's answers to earlier prompts of this command (point 5); empty on the first send.

**Answer** (one of two, HTTP 200):

- `done`: `output`, an ordered list of `[stream, text]` chunks, and `exit_code`. Chunks keep the order in which the command wrote to stdout and stderr, so a terminal showing both sees what local mode shows.
- `prompt`: the output so far, the prompt text, the stream it is written to (stderr under `--json`, as Click and `confirm` do locally), and its digest (point 5). Nothing was written.

A `503 {"not_executed": "retiring"}` stays the only refusal after which the shim may run the command itself (ADR-1052, points 2 and 13). The vocabulary hash is not sent: the shim parses nothing, and the daemon parses with the configuration it fingerprinted, which the retirement check holds to the files on disk.

### 2. The daemon runs the CLI in process, and its commands call the daemon's operations

- **The Typer app is built once, at daemon start-up.** It needs no cache keyed on the vocabulary: any edit to `.squads.toml` or `.overrides/` retires the daemon (ADR-1052, point 13), so the app never outlives the vocabulary it was built from.
- **The API inside a served command is the daemon's own `LocalApi`,** bound on the request's `RequestContext` before the root callback runs. It reuses the normal-mode service composed at start-up and, per call, the steps of ADR-1225 section 7 that apply in process: the schema grant, the composition mode, the read scope. No fork, no subprocess, no HTTP call to itself. `select_api` refuses to run inside a served command, and a `tests/meta` guard holds that the endpoint's modules import neither `squads._cli._remote`, `http.client` nor `subprocess`.
- **The squad is the daemon's.** A served command never walks up from `cwd`, resolves `-C` or reads any path the client names: `cwd` seeds `start_dir`, which spells paths in messages (ADR-1225 section 9), and `client_dir` is bound as the effective directory as given, with no filesystem read. Client files arrive as attachments. ADR-1052 point 6 holds: a caller of a TCP listener reaches the squad and nothing else.
- **Rendering happens in the daemon.** Each request gets its own consoles, built from `terminal`, so colour, width, box characters and wrapping are decided as the client's own process would. At start-up the daemon replaces `sys.stdin`, `sys.stdout` and `sys.stderr` with proxies that write to the current request's capture and read from its answers, and fall back to the daemon's log outside a request. The stdout and stderr proxies accept `bytes` as well as `str`, because Click and Typer write bytes on the completion path. It replaces `os.environ` the same way: inside a served command, a name on the fixed list reads the request's `env` (absent when the client did not send it), and every other name reads the daemon's own. `print()`, Click, Typer's completion, Rich and `actor.session_from_env()` then need no change. A `tests/meta` guard holds that no `squads` module reads an environment variable at import time, where the proxy cannot reach it. The guard is load-bearing: in the prototype, `_spans` read `SQUADS_SPANS` from the daemon's own environment at import, and a daemon started under it printed spans into every served command's stderr.
- **Notices raised inside an operation** (ADR-1225 section 3) print through the sink the root callback sets, which in a served command is the request's stderr capture; they land in the output in the order local mode prints them.
- **Execution is serial.** A served command runs on a worker thread (the server's loop cannot run `asyncio.run`) and holds the daemon's one serial lock (ADR-1225 section 7) for its whole run, parse to render, so writes order against route requests as they do today. Nothing in the design above relies on that lock: consoles, context, stdio proxies and Click's stack are per request or per thread, so concurrent served commands remain ADR-1052's change condition, at the cost of the worker pool.

### 3. Attachments and stdin

- **The shim's file-argument table** names what is a client file: the `--file` option, by name, wherever it appears (custom-type commands included), and `import`'s first argument. The table is a literal in the shim's module; a `tests/meta` guard holds it equal to the parameters declared through the shared `--file` helper and to `import`'s signature.
- An attachment is the file's bytes, base64, keyed by the argument exactly as written. In the daemon `read_client_text` serves it and decodes it as local mode does (UTF-8, with the same refusal text for invalid bytes). A name the request does not carry is refused with an internal error: it means the table is incomplete, which the guard prevents.
- **Stdin (`-`).** When a file argument is `-`, the shim reads its stdin to the end and attaches it under `-`, decoded in the daemon with the client's stdin encoding. A prompt later in the same command then reads end of input and aborts, as it does locally once stdin is consumed.
- A file the shim cannot read (missing, a directory, no permission) makes it run the command locally (point 6), so the error text is local mode's own.

### 4. The client is a shim

`squads.__main__:main` becomes the shim. It imports the interpreter's standard library, `squads` (whose `__init__` holds only `__version__`), `squads._endpoint` and the shim's own module, and the standard-library parts of `squads._daemon_link` it needs, and nothing else. A `tests/meta` guard runs it in a subprocess on two paths, a live daemon answering and a cold start up to the daemon's ready line, and fails on any other `squads` module or third-party package in `sys.modules`. The start path is standard library only: its stale-lock probe uses `fcntl.flock` on POSIX and `msvcrt.locking` on Windows, the primitives `filelock` uses in the daemon, so the two interoperate. Its overhead is held to the budget of point 10.

The shim, in order:

1. Answers a bare `--version`, as today.
2. Reads `-C`/`--dir` from `argv` with the CLI's own hoisting rule; a `tests/meta` table test holds the shim's extraction equal to the root callback's over every accepted spelling.
3. Runs locally, without contacting a daemon, when the first command token is in the **local-only table**: `init`, `adopt`, `daemon` and `ui`. A `tests/meta` guard holds the table to the registered root commands and to the operations marked `local_only`.
4. Resolves the `Endpoint` (ADR-1052, point 9). No squad, the daemon off, or `SQUADS_DAEMON=off`: local.
5. Connects, starting the daemon if none is live (ADR-1052, point 11), reads attachments, sends with the answer timeout of the command's class (ADR-1225 section 3), and writes the answer: each chunk to its stream, through the CLI's Windows UTF-8-with-replacement stream setup, then exits with the code.

**The timeout class.** The shim parses nothing, so it holds a literal table of the command paths whose operation is classed `long` (`migrate up`, `repair`, `import` and the rest); every other command is `standard`. A `tests/meta` guard holds the table equal to the commands bound to `long` operations in the operation table.

`--help`, `docs`, `migrate help` and shell completion are served like any command: the daemon answers them from the Typer app and vocabulary it holds, which are the checkout's, and a completion that cannot reach a daemon before sending falls back locally. A Tab press therefore never rebuilds the spec-derived command tree in the client.

### 5. Prompts: two phases, nothing written before the answer

- A served command that reaches a prompt with no matching answer stops there and answers `prompt`. It has written nothing, because every prompt precedes the writes of its command (fact 6). The daemon enforces it: a prompt reached after a non-`GET` operation has run in the same request is an internal error, so the post-commit prompt branch cannot occur silently.
- The shim writes the output, shows the prompt text, reads one line from its stdin (or end of input) and sends the same request again with that answer appended to `answers`. The shim holds no prompt logic of Click's; the daemon parses the line as Click does, and an invalid line comes back as another `prompt` carrying Click's error text.
- **The rerun starts from scratch.** The prompt's digest covers the output written before it plus its text. An answer is fed to a prompt only when the rerun reaches that prompt with the same digest, so a confirmation applies only to the screen the user saw; on a different screen (a comment edited in between), the daemon answers `prompt` again with the full new output. When the digest matches, the answer leaves out the output already shown.
- **A daemon lost between the phases** wrote nothing, so the shim falls back: it runs the command locally from the start, and the user is asked again in local mode.

### 6. Fallback: local before sending, never after

- **Before the request is sent** the shim runs the command locally: no daemon and a failed start (with ADR-1052 point 11's one line on stderr), a refused or reset connection before the request is fully written, a file it cannot read (point 3), and a `503 not_executed` answer. Running locally means importing `squads._cli` in the same process and calling `run(argv)`: the same code with the same output.
- **After the request is sent** nothing is replayed. A lost connection, a timeout or Ctrl-C prints ADR-1225 section 3's "the operation may still complete" error and exits 1, or 130 on Ctrl-C. A `prompt` answer is the one point after sending at which nothing has run to completion, which is why point 5 may fall back there.
- The shim keeps no memory between invocations: no failed-start record and no cached endpoint.
- **The start bound stays 5 s.** A cold start measured 1.1-1.3 s for spawning the daemon and answering the first `show`; 5 s is the ceiling for a slow host, not the expected wait, and it is reached only by a start that is failing.

### 7. The daemon's cache of parsed files

The daemon keeps, across requests, three results the read path computes:

- **the index**: the validated `SquadsDB` parsed from `.squads.json`;
- **item frontmatter**: per item file, the parsed frontmatter mapping;
- **the override's check against the index** (`validate_against_index_fail_closed`): 40-80 ms, and a command runs it twice (root callback and command resolution), re-reading the index and walking the corpus each time. Its outcome, success or the refusal, is memoised by the index's digest and the identity of the daemon's spec.

The merged workflow spec is not re-read per request either: a served command takes it from the daemon's start-up documents, which the retirement fingerprint ties to the files on disk (ADR-1052, point 13). In the prototype, without the validation memo and the start-up spec the handler of `task show` took 250-320 ms; with them, 126 ms.

Rules:

- **Keyed by content, not by stat.** An entry is keyed by its path and a BLAKE2b digest of the bytes the read path has just read. A read still reads the file (23 ms for every item file, 5-7 ms with the hash for the index; fact 4) and skips only the parse on a digest hit. Nothing is validated in advance: the read itself is the validation, so a change by git, an editor, another installation or a local-mode CLI is seen by the next read, with no dependence on a filesystem's timestamp granularity or inode reuse.
- **Reads only.** The cache is consulted where `IndexStore.load` and the item-file read parse; `transaction()` keeps re-reading from disk under the file lock and never consults it. It is never a source of truth, and dropping it at any moment changes nothing but time.
- **Bounded by the corpus:** one entry per path, replaced when its digest changes; an entry for a path no longer read is dropped when the daemon next scans the corpus. Entries cannot be mutated through what a caller receives. A hit is not paid per load: an index hit costs about 13 ms to copy or unpickle at this corpus size, and one request loads the index several times, so a request receives one value, shared by every load in that request (frozen, or one copy per request), never a copy per load. Frontmatter copies are cheap enough per hit.
- **Threaded, not global.** The cache hangs off the daemon's state and reaches the store through the `RequestContext`; it is not module-level state, and local mode has none.
- Out of scope: caching `check`'s rule results, which span items. With the three results cached, `check`'s handler measured 1.6 s against 7.0 s locally (point 10); its rule work is most of what remains.

### 8. HttpApi and the resource routes stay, for every other client

- The resource routes of ADR-1225 remain the daemon's public API: the TUI, the web front and FEAT-33's hosted squad call them. Served commands and routes call the same operations through the same binding table.
- `HttpApi`, endpoint re-resolution and the vocabulary hash stay for the TUI (ADR-1224, point 7), which runs in the client's process.
- The CLI's own selection of `HttpApi` goes: a CLI process is either the shim's local fallback or a served command, both on `LocalApi`. `call()` keeps taking an `Api` handed in on the context, which is how a test harness drives the CLI through `HttpApi` (point 9).

### 9. Tests (ADR-1172)

- **Endpoint parity:** the mode-parity run of `tests/cli` goes through the command endpoint: the harness sends each case's `argv` to the daemon application served on a thread against the copied squad and asserts the same exit code and whole output. The harness builds one Typer app per session, as the daemon does once per start. A test's frozen clock reaches the served command through the harness, which binds it on the request's context in process; it never travels on the wire, and the daemon never reads the test process's state. Its jobs are ADR-1172's four (bundled squad on Linux, macOS and native Windows, override squad on Linux).
- **Route parity:** `tests/cli` run once more with an `HttpApi` handed to the root callback, on Linux only, so every operation stays covered over HTTP although the CLI no longer selects it.
- **Endpoint tests** under rules 4-6, without `covers` markers: each answer kind; a completion request for bash, zsh and fish answering local mode's candidates; ordered chunks; an unattached name; stdin attached under `-`; a prompt answered, refused, invalid, and a changed screen between phases; a prompt reached after a write, refused, through a test-only command that writes then confirms, which the endpoint harness registers as a fixture (no CLI command reaches that branch; an exception to ADR-1172's surface-only rule, recorded here); the browser port refusing the endpoint.
- **Cross-process set**, added members: the shim falling back on a refused connection; the daemon killed between the two phases of a prompt, the shim asking again locally with nothing written; the local-only table never contacting a daemon. Implicit start, no replay, Ctrl-C and the Windows detached spawn stay members.
- **Guards:** the shim's import set; the file-argument table; the local-only table; `-C` extraction; no self call from the endpoint; no environment read at import time.
- **Cache:** an in-process test per cached result: a file changed between two requests with the same size and timestamp, read back current; an override check refused, then rerun once the index digest changes.

### 10. Prototype and the client budget

The prototype (python-dev comment 814b56a on this decision) built the shim, the endpoint, the stdio and environment proxies and the three cached results, without attachments, prompts, the Windows transport or Ctrl-C. Measured on 2026-10-30 on the WSL2 development host (load average 1.0-1.3, bare interpreter 22 ms median), a copy of this repository's squad, 31 interleaved runs, whole-process wall time, medians with p25-p75:

| Scenario | Local | Shim and daemon | Daemon handler | Shim overhead |
|---|---|---|---|---|
| `task 1219 show` | 740 (701-792) | 221 (192-234) | 126 (104-136) | 91 (78-102) |
| `list --json` | 631 (602-673) | 174 (157-188) | 83 (65-97) | 92 (75-104) |
| bash Tab on `sq task 1219 ` | 359 (336-370) | 108 (89-115) | 21 (16-25) | 83 (72-91) |
| `check`, caches warm | 6,989 (6,782-7,370) | 1,751 (1,653-1,847) | 1,645 (1,562-1,770) | 97 (77-108) |

- Output, error text and exit code were byte-identical between the modes on twelve cases, completion and `--help` among them.
- A cold start (spawn the daemon, answer the first `show`) took 995 ms (901-1,075). The first `check` after a start took about 4.4 s, the next ones 1.5-2.0 s.
- **Where the shim's 91 ms goes:** the interpreter 22 ms; importing the shim with `squads._endpoint` about 36 ms over the bare interpreter; endpoint resolution about 30 ms, most of it the version lookup through `importlib.metadata` and the TOML parse with their imports; the socket round trip about 3 ms; exit and output writing the rest.

**The budget,** a release criterion for TASK-1219 ST8, replacing ADR-1225's 275/235 ms: the shim's overhead, the process's wall time minus the daemon's handler time sent with the answer, as the median of 31 interleaved runs of `sq task <n> show` on the reference host, is at most **100 ms**. One figure covers human output, `--json` and completion, because the shim does the same work for all three.

- **The reference host** is the GitHub-hosted Linux runner of the budget-report CI job (TASK-1220), which is reproducible by anyone and already runs the report. Earlier runs there measured about 1.3 times this development host.
- **Why 100 ms.** As built, the shim's 91 ms here projects to about 120 ms on the runner. The lean `_endpoint` split brings it to about 60 ms here (an estimate of the prototype, not built), about 80 ms on the runner. 100 ms requires the split and leaves about 20 ms for runner noise.
- **The lean split:** the shim's path imports no `dataclasses`, `typing` or `importlib.metadata`. The squad key takes the version from `squads.__version__` and the package directory from `squads.__file__`. The shim's import guard names those three modules.
- The benchmark script and the CI report of ADR-1225 section 5 measure this figure instead of the old one; CI still reports, the release runbook checks.

## Amendments to ADR-1052, ADR-1224 and ADR-1225

Applied on acceptance, each in place under board rule 6 (a clause-level change; linked `related`).

**ADR-1052**

- Context: the 2026-10-28 reversal gains the 2026-10-30 direction: a private command endpoint for the CLI beside the resource routes.
- Point 1: `POST /v1/commands` returns as this decision's point 1, on the CLI listener only.
- Point 6: the browser port never serves the endpoint; attachments keep TCP callers away from the owner's other files.
- Point 9: the remote client is the shim (this decision, point 4), not the CLI calling `HttpApi`; the local-only list becomes the shim's table (`init`, `adopt`, `daemon`, `ui`), and shell completion, `--help` and the package-data commands are served; the forwarder's file-argument table returns as point 3.
- Point 10: the shim writes the received output in chunk order through the Windows stream setup; fallback per point 6; prompts per point 5.
- Point 11: the 5 s start bound is kept with its reason.
- Point 12: "no squad data is kept between requests" becomes "only the three cached results of point 7, keyed by content and never a source of truth". The change condition "an index snapshot kept across commands" is met by it and is removed. `needs_terminal` returns, two-phase.
- Consequences: remote mode's cost is the shim's budget; the "renderer in another process" parity question returns, answered by terminal facts, the request's `env` and endpoint parity.

**ADR-1224**

- Point 4, "Which API a command uses": a CLI process uses `LocalApi`; a harness may hand it another `Api`. `HttpApi`'s callers are the TUI and tests.
- Point 7: unchanged in substance; the TUI is now `HttpApi`'s only production caller.
- Consequences: "The remote client never imports `_services`" becomes "the shim imports no `squads` module beyond `_endpoint`"; the client import guard is replaced by the shim's.

**ADR-1225**

- Context and section 4: "the command endpoint" is no longer the rejected alternative for the CLI; it is rejected only as the public API, which stays the routes.
- Section 5, "Choosing between the HTTP and the local call": applies to the TUI only; the CLI follows this decision's points 4 and 6, so `docs`, `migrate help`, `migrate chlog`, `--help` and completion are served rather than kept off the daemon. "The forwarder in `squads.__main__` goes" is reversed. Parity: as this decision's point 9.
- Section 5, "What the client reads": the CLI client reads only what endpoint resolution reads; the vocabulary hash is sent by the TUI and hosted clients, not the CLI.
- Section 5, "The client budget": replaced by this decision's point 10 (100 ms of shim overhead on the GitHub-hosted Linux runner); the levers stay for local mode; the import guard becomes the shim's.
- Section 7: a served command runs inside the serial lock on a worker thread (point 2).
- Section 9: attachments, terminal facts and the prompt signal return in the form of points 1, 3 and 5; `run(argv)` is what both the daemon and the shim's fallback call.
- Options rejected: "Keep `POST /v1/commands` beside the routes" is reversed for the CLI; the endpoint stays private, so the web front still has one protocol.

**ADR-1172**

- Mode parity: the remote-mode run goes through the command endpoint, plus one Linux route-parity job (point 9).
- Cross-process set: the members of point 9 join.

## Consequences

- A remote command costs the shim (91 ms measured, 100 ms budgeted on the reference host) plus the daemon's work, which now includes parsing and rendering on a warm interpreter: `task show` 740 to 221 ms, `list --json` 631 to 174 ms on the development host. Local mode is unchanged apart from the shim's resolution step before it imports the CLI.
- Output is the same code's output in both modes, so parity rests on the terminal facts and environment reaching Rich, not on a second renderer.
- `check` drops from 7.0 s to 1.75 s on this squad once the caches are warm; its rule work is untouched.
- Two daemon surfaces call one set of operations: the private endpoint for this installation's CLI, the public routes for everything else.
- The removed TASK-1217 machinery comes back in a narrower form: attachments keyed by argument, terminal facts, and a prompt that never runs after a write.
- TASK-1219 ST8's budget becomes point 10's; its client-side levers keep their value for local mode.

## Options considered and rejected

- **Keep the CLI on `HttpApi` and trim its imports further.** Measured at 311-337 ms against a 275 ms budget after the `_ops` split, with the remaining levers estimated at 30-45 ms together: still about 0.3 s, against a 13 ms interpreter.
- **Cache keyed by `(inode, mtime_ns, size)`, validated by a stat walk per request.** 2-6 ms against 39-59 ms for read and hash, but it misses a same-size rewrite within one timestamp tick or onto a reused inode, and its cost on NTFS and APFS is unmeasured. The read is already paid wherever a file is parsed, so content keys cost only the hash. Kept as the change condition below.
- **The shim waiting for nothing: start the daemon and run the first command locally.** Saves about 0.5 s once per idle period, but needs a failed-start record between invocations to avoid spawning on every command.
- **Patching `os.environ` and the standard streams per request.** Correct only under serial execution, and leaves the daemon's own logging racing the request; context-routed proxies installed once cost the same and do not tie the design to the lock.
- **Shell completion in the client.** Each Tab press would import the CLI and rebuild the spec-derived Typer app, about 0.7 s, which is the cost the shim exists to avoid.
- **Serving the endpoint on the browser port.** It would give the web front a second protocol and expose argv-level access to pages.

### What would change this decision

- The hash dominates a corpus-wide read on some host: an `(inode, mtime_ns, size)` pre-check in front of the read.
- Served commands queue behind each other measurably: the worker pool.
- A hosted squad (FEAT-33): the endpoint is private to one installation, so a hosted squad's CLI uses the routes and the vocabulary hash, as ADR-1225 decides.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
- [2026-10-30T19:13:26Z] `architect` Robert Architect:
  - @manager drafted from the 2026-10-30 frame (FEAT-1140 c2dced7) and your two cache inputs, which are in. Where the ADR departs from the frame, and why:
    - Cache key: content digest of the bytes the read already reads, not `(inode, mtime_ns, size)` plus a stat walk. Measured here: read+hash of all 1,317 files 39-59 ms against stat 2-6 ms, but the read is already paid wherever a file is parsed, and the stat key misses a same-size rewrite inside one timestamp tick or onto a reused inode. It also closes the unmeasured NTFS/APFS stat question. The stat key is kept as the change condition. Operator question 3.
    - No per-vocabulary-fingerprint cache of the Typer app: any vocabulary edit retires the daemon, so the app is built once at start-up.
    - No vocabulary hash on the endpoint: the shim parses nothing, and the retirement check already ties the daemon's vocabulary to the files on disk.
    - Process-global stdio and `os.environ` are not patched per request: stdio proxies plus one env accessor, so the design does not depend on the serial lock. Execution is still serial (worker thread inside the lock).
    - Output is an ordered list of stdout/stderr chunks, not two strings, so a terminal shows both streams in local mode's order.
    - Prompts: the daemon refuses a prompt reached after a write, at runtime, rather than leaving the post-commit branch untested; an answer applies only when the rerun shows the same screen (digest).
    - The 5 s start bound is kept; the no-wait start is listed as rejected (needs a failed-start record between invocations).
    - "editor" in the local-only list matches no command; asked as question 4.
- [2026-10-30T19:13:27Z] `architect` Robert Architect:
  - @op-pierre four questions at the end of the body (completion local or served, the Linux route-parity job, the cache key, what "editor" names). Next step is the measured `task show` prototype in a worktree (section 10); the shim's budget for TASK-1219 ST8 is set from it.
- [2026-10-30T19:21:21Z] `op-pierre` Pierre Chat:
  - Answers to the open questions (2026-10-30):
    1. Completion is served by the daemon, by the same rule as any command (start one if needed, local fallback before sending). Local completion would rebuild the whole spec-derived Typer app on every Tab press, which is what the shim exists to avoid. Add the completion environment variables to the fixed env list.
    2. Keep one Linux job that runs tests/cli through HttpApi: the TUI and the web front depend on the routes.
    3. Cache key: the content digest, as the ADR decides.
    4. "editor" is dropped from the local-only list; it names no command.
- [2026-10-30T19:22:45Z] `architect` Robert Architect:
  - Body amended 2026-10-30 per op-pierre f9a373e: completion is served (bash/zsh/fish completion variables join the env list, the local-only table is `init`, `adopt`, `daemon`, `ui`), the Linux route-parity job and the content-digest key stand, "editor" is gone, and the open-questions section is removed. Served completion needs Typer's completion code to read the request's variables from `os.environ`, so the per-request env accessor is replaced by an `os.environ` proxy installed at start-up, like the stdio proxies; its guard is now "no environment read at import time". The prototype also times a Tab completion. @manager
- [2026-10-30T20:03:24Z] `op-pierre` Pierre Chat:
  - Overnight delegation (2026-10-30): the manager runs the full loop on ADR-1261 (prototype, acceptance decision, breakdown, implementation, review, docs) without waiting for me.
- [2026-10-30T20:21:24Z] `python-dev` Elias Python:
  - Prototype results for section 10 (worktree `/home/pchat/projects/squads/.claude/worktrees/agent-ab8070e632116d3ff`, branch `worktree-agent-ab8070e632116d3ff`, throwaway spike on release/0.19).
    
    Method: copy of this repository's squad (1,317 item files, 2.1 MB index) under `~/.cache/sq-proto-1261/copy`, daemon on the copy only. 31 interleaved runs per scenario, local mode (`SQUADS_DAEMON=off`) against shim+daemon, wall time of the whole process, non-tty pipes. Handler = time the daemon spent in the served command (parse to render, serial lock excluded). Host load average 1.0-1.3 before and after (a busy shared WSL box: the bare interpreter measured 16/22/24 ms p25/median/p75, not 13). Stdout, stderr and exit code were byte-identical between modes on 12 cases (show, show --json, list, list --json, an error, check, --help, task --help, tree, board list, inbox, bash completion).
    
    Medians in ms, p25-p75 in brackets:
    
    | Scenario | Local wall | Shim+daemon wall | Daemon handler | Shim overhead (wall - handler) |
    |---|---|---|---|---|
    | task 1219 show | 740 (701-792) | 221 (192-234) | 126 (104-136) | 91 (78-102) |
    | list --json | 631 (602-673) | 174 (157-188) | 83 (65-97) | 92 (75-104) |
    | bash Tab `sq task 1219 ` | 359 (336-370) | 108 (89-115) | 21 (16-25) | 83 (72-91) |
    | check, frontmatter+index cache warm | 6,989 (6,782-7,370) | 1,751 (1,653-1,847) | 1,645 (1,562-1,770) | 97 (77-108) |
    
    Cold start (no daemon; first `show` spawns it and is answered): 995 ms median (901-1,075, 5 runs). First `check` after a start (cache cold): about 4.4 s; the second 1.5-2.0 s.
    
    Where the shim's ~90 ms goes (measured pieces): bare interpreter 22; importing `squads._shim` (`squads._endpoint` plus stdlib) 58 wall, so about 36 over bare; `endpoint_for` on top about 30 (shim_resolve span 16 ms median in process, the rest is the version lookup through importlib.metadata and the toml parse as the wall figure includes their imports); socket round trip minus handler about 3; process exit and output write the remainder.
    
    Verdict: the ~30-40 ms estimate is NOT met as written. With `_endpoint` unchanged the shim costs 80-100 ms: about 2.5x the estimate, but under a third of the old 275/235 ms budgets. Budget to set from this prototype: 100 ms median on this host as built; about 60 ms is the realistic floor if `_endpoint` is split lean (no dataclasses/typing, no importlib.metadata for the key, which is the larger part of the 36 ms import and the 30 ms resolve). That lean split was not built or measured. Whole-command gain: show 740 -> 221, list --json 631 -> 174, completion 359 -> 108, check 6,989 -> 1,751. The old per-command client budgets (275 human / 235 --json total overhead) are met: 91-92 ms.
    
    Findings in ADR-1261:
    1. Environment at import time: the daemon's `_spans` read `SQUADS_SPANS` from the daemon's own environment, so a daemon started under it printed spans into every served command's stderr. The proposed `tests/meta` no-env-read-at-import guard covers it; `SQUADS_SPANS` must not be on the forwarded list for the same reason unless `_spans` becomes request-scoped (the prototype kept it off the list and the shim prints the handler span itself).
    2. The cache alone does not give the budget. Each served command ran `validate_against_index_fail_closed` twice (root callback and command resolution), 40-80 ms each, re-reading and parsing the index and walking the corpus; and `_read_spec_from_disk` re-merged the override. The prototype memoises the validation by (index digest, spec identity) and takes the spec from the daemon's sources. Without both, the handler was 250-320 ms. The ADR's section 7 should list a third cached result (override-versus-index validation), or the handler budget is wrong.
    3. Unpickling the cached index costs about 13 ms per hit and a request makes several `fresh`/unscoped loads; copies-on-hit are not free at this corpus size. Frontmatter copies were cheap enough to win clearly (check handler 7.0 s to 1.6 s).
    4. Click and Typer write bytes to the stream in the completion path, so the stdout proxy must accept `bytes` as well as `str` (an intermittent 500 until fixed). `prog_name` must travel with the request: Typer derives the completion variable and usage text from it.
    5. `asyncio.run` per served command on a worker thread, with the cached `LocalApi` service reused across loops, worked on this corpus (no cross-loop errors seen over roughly a thousand requests).
    6. Not built: attachments, stdin `-`, two-phase prompts, Windows TCP transport, terminal width on a tty beyond forwarding COLUMNS/LINES, Ctrl-C. The shim runs `import` and any `--file` command locally for now. The stdout/stderr proxy and `os.environ` replacement worked for print, Click echo, Rich and `actor.session_from_env`, but cache entries here are keyed by path+digest only for frontmatter and a single slot for the index (no eviction scan).
    7. Daemon start on the first command spawns `python -m squads daemon run` through the shim; this works because `daemon` is in the local-only table. A daemon accidentally started on the worktree's own squad (a shell run without `-C`) shows the shim resolves the squad by walk-up from cwd, as intended.
- [2026-10-30T20:23:32Z] `architect` Robert Architect:
  - Body amended 2026-10-30 from the prototype (814b56a). Section 7 now caches three results: the index, the frontmatter, and the override's check against the index, memoised by index digest and spec identity. The merged spec comes from the start-up documents, and a request gets one shared index value instead of a copy per load. `SQUADS_SPANS` and `SQUADS_DAEMON` are never forwarded, and the import-time env guard is load-bearing. The stdout and stderr proxies accept bytes, and `prog_name` travels with the request. Section 10 records the measured figures and sets TASK-1219 ST8's budget at 100 ms of shim overhead (wall minus handler, median of 31 `task show` runs) on the GitHub-hosted Linux runner. As built the shim projects to about 120 ms there, so meeting the budget requires the lean `_endpoint` split (no `dataclasses`, `typing` or `importlib.metadata` on the shim's path). @manager
- [2026-10-30T20:23:59Z] `manager` Catherine Manager:
  - Accepted under the operator's overnight delegation (2026-10-30): the prototype met the direction (task show 740 to 221 ms, check 7.0 to 1.75 s, output byte-identical on twelve cases; manager spot-check about 830 to 250 ms) and its findings are folded into sections 7 and 10. @architect apply the listed amendments to ADR-1052, ADR-1224, ADR-1225 and ADR-1172.
- [2026-10-30T20:33:11Z] `tech-lead` Olivia Lead:
  - - Breakdown is TASK-1262 to TASK-1266 (FEAT-1140, 2026-10-30). Points the body leaves open, each with what the tasks do unless you rule otherwise:
      1. Answer timeouts in a shim that parses nothing: ADR-1225's `standard`/`long` classes need the command's class. TASK-1264 ST4 builds a literal table of the `long` command paths in the shim, guarded equal to the operations classed `long`.
      2. A prompt reached after a write (point 9's endpoint test): no CLI command reaches it. TASK-1262 ST5 serves a harness app with one test-only command that writes then confirms; confirm that this exception to the surface-only rule is acceptable.
      3. `-C` in a served command: applying it to `cwd` for path spelling may stat a client-named path, which ADR-1052 point 6 forbids a TCP caller. TASK-1262 asks the developer to do it without a filesystem read or stop and ask.
      4. The shim's import guard: holds the path to a live daemon; the start path adds `_daemon_start` and parts of `_daemon_link`, and its `filelock` use must become stdlib. The guard text names three modules but not which path it runs.
      5. The `prompt` answer: which stream the prompt text goes to is not specified (Click writes it to stderr under `--json`). TASK-1262 ST5 adds the stream to the answer.
      6. The parity harness: the test fixtures freeze the clock on the test's context, which a served request does not carry; TASK-1262 ST6 carries it through the harness, never through the daemon reading the test process.
      @architect
- [2026-10-30T20:35:40Z] `architect` Robert Architect:
  - Rulings on 64eadba (2026-10-30). The body is amended in place for each, and the status is unchanged. @tech-lead
    1. Timeouts: yes. The shim holds a literal table of the command paths whose operation is `long`, guarded equal to the operation table (point 4).
    2. Prompt after a write: accepted as an endpoint-harness fixture (one test-only command that writes, then confirms). It is recorded in section 9 as an exception to ADR-1172's surface-only rule.
    3. `-C`: the request carries `client_dir`, the absolute directory the shim already resolved from `cwd` and `-C`. The daemon binds it as given, with no filesystem read, and does not apply `-C` again. If the shim cannot resolve `-C`, it runs the command locally (points 1 and 2).
    4. Import guard: it runs both the live-daemon path and the cold-start path up to the ready line. Both are standard library only. The stale-lock probe uses `fcntl.flock` or `msvcrt.locking`, the primitives `filelock` uses in the daemon, so the two interoperate (point 4).
    5. The `prompt` answer names the stream its text is written to, as local mode does (stderr under `--json`) (point 1).
    6. Parity harness: one Typer app per session, and the frozen clock is bound on the served request's context by the harness in process, never on the wire (point 9).
    7. `docs/api.md` says only that the CLI uses a private channel outside the API, with no wire format (point 1).
<!-- sq:discussion:end -->
