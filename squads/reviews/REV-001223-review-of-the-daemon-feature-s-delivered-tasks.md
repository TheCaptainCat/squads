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
  status: Deferred
  severity: medium
  deferred_to: TASK-1227
- local_id: F4
  title: No test covers terminal facts reaching the consoles; build_consoles(None)
    mutation survives
  status: Deferred
  severity: medium
  deferred_to: TASK-1227
- local_id: F5
  title: Override remedy path still spelled from the process directory in a served
    request
  status: Verified
  severity: low
- local_id: F6
  title: Prompt after a committed transaction does not fail as ADR-1052 point 12 states
  status: Deferred
  severity: low
  deferred_to: TASK-1227
- local_id: F7
  title: Attachments decoded outside the CLI; invalid UTF-8 --file escapes as a traceback
  status: Verified
  severity: low
- local_id: F8
  title: Comment-removal listing before NeedsTerminal; vacuous --version stderr row
  status: Deferred
  severity: info
  deferred_to: TASK-1229
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
created_at: '2026-10-28T18:45:17Z'
updated_at: '2026-10-28T22:31:29Z'
---
<!-- sq:body -->
Batch review of FEAT-1140's delivered tasks, one commit at a time, against ADR-1052 and each task's acceptance.

## Scope

- TASK-1217, commit 22ce7f65: the in-process command entry (`run`), per-invocation consoles, the request-seeded `RequestContext` (start directory, attachments, terminal facts, documents), attachment-served file reads, and the prompt helper that signals `NeedsTerminal`.
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
<!-- sq:discussion:end -->
