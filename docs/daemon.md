# The daemon

squads can keep one long-lived process per squad, the **daemon**, that runs the squad's commands
and serves the squad over a local HTTP API. The CLI hands it each command line, so a command skips
the start-up work a fresh process repeats every time, and any other client (the terminal browser,
a script, a web front) calls the same operations through the API. This page covers how the CLI uses
the daemon, how to configure and inspect it, what it keeps on your machine, and who can reach it.
The API itself is described in [api.md](api.md).

## Remote mode and local mode

Each `sq` command runs in one of two modes, chosen once when it starts:

- **Remote mode.** `sq` sends the command line to the squad's daemon, which parses it, runs it and
  renders its output, then prints what the daemon sends back and exits with its exit code. If no
  daemon is running, the command starts one and waits for it. Later commands find the same daemon.
- **Local mode.** The command runs in your own process, reading and writing the squad files
  itself.

Both modes run the same code, so the output and the exit code are the same, `--json` included. The
daemon renders for your terminal: `sq` sends whether each of its standard streams is a terminal,
their encodings and the terminal's size, and the environment variables listed under
[The environment of a command](#the-environment-of-a-command). A write made in one mode is visible
to a command in the other mode straight away: both take the same file lock, and the daemon reads
the files again for every command (see [What the daemon keeps between commands](#what-the-daemon-keeps-between-commands)).

Remote mode applies when the daemon is enabled (it is by default, see
[Settings](#settings)). Local mode applies when it is disabled, when the command is not inside a
squad, and when a daemon cannot be used (see
[When the daemon cannot be used](#when-the-daemon-cannot-be-used)).

Every command goes to the daemon, `sq --help`, `sq docs`, `sq migrate help`, `sq migrate chlog`
and shell completion included, and starts one if none is running. These always run locally and
never start or contact a daemon:

- `sq --version` on its own;
- `sq init` and `sq adopt`, which create a squad;
- `sq daemon`, which talks to the daemon itself;
- `sq ui`, the terminal browser, which runs in your terminal and chooses for each request it makes,
  by the rules on this page, whether to call the daemon's API or answer in its own process, so a
  daemon that stops or retires while it is open is found or started again at its next request;
- `sq --install-completion` and `sq --show-completion`, which act on your own shell.

### Files a command reads, and prompts

The daemon never reads a path you name. When a command takes a file, `sq` reads it on your side and
sends its content with the command line: the value of `--file` on any command, `-` (standard input)
as that value, and the file `sq import` takes. A file that cannot be read makes the command run in
local mode, which reports it as it always does:

```
error: cannot read file '../notes.md': No such file or directory
```

Prompts, such as the confirmation before a removal, are asked in your own terminal. The daemon
stops at the prompt before the command has written anything, `sq` shows what the command printed
and the question, reads your answer, and sends the command again with it. The daemon runs the
command again from the start and applies your answer only if the command shows the same screen
again: if what you were asked about changed in between (a comment edited by someone else, for
example), you are asked again with the new screen. If the daemon stops between the question and
your answer, nothing has been written, so the command runs in local mode from the start and asks
you again.

### The environment of a command

A command run by the daemon sees your values of these environment variables, and no other
variable from your shell:

- `SQUADS_SESSION_ID` and `SQUADS_PARENT_SESSION_ID`, which the reflog records;
- `SQUADS_SPANS`, the timing switch: the daemon prints the command's spans only when you set it;
- the variables that change how output is rendered: `NO_COLOR`, `FORCE_COLOR`, `CLICOLOR_FORCE`,
  `PY_COLORS`, `GITHUB_ACTIONS`, `TTY_COMPATIBLE`, `TTY_INTERACTIVE`, `COLUMNS`, `LINES`,
  `TERMINAL_WIDTH`, `_TYPER_FORCE_DISABLE_TERMINAL`, `TERM` and `COLORTERM`;
- the shell-completion variables of bash, zsh and fish: `_SQ_COMPLETE`, `_SQUADS_COMPLETE`,
  `COMP_WORDS`, `COMP_CWORD`, `_TYPER_COMPLETE_ARGS`, `_TYPER_COMPLETE_WORD_TO_COMPLETE` and
  `_TYPER_COMPLETE_FISH_ACTION`.

`SQUADS_DAEMON` acts on your side only: it chooses the mode before anything is sent (see
[Settings](#settings)).

### What differs between the modes

The output is the same; the timing and Ctrl-C are not.

- **Output arrives when the command ends.** A remote command prints nothing until the daemon
  answers, then prints everything the command wrote, stdout and stderr in the order it wrote them.
  A notice raised while the command runs, such as `warning: waiting for the index lock <path>…`,
  is printed then, before the result. In local mode it is printed as it happens. The lines are the
  same.
- **Ctrl-C ends the wait, not the command.** In remote mode, Ctrl-C stops `sq` waiting for the
  daemon. A command the daemon has already started runs to completion, so a write may still be
  applied. `sq` prints

  ```
  error: no answer from the squad served at <endpoint>; the operation may still complete. Check its result before running it again.
  ```

  and exits `130`. Check the result (with `show`, `list` or `sq reflog`) before running the command
  again. In local mode, Ctrl-C ends the process.
- **Timeouts.** A remote command waits at most 5 seconds to connect to the daemon, and at most 300
  seconds for its answer, including any time spent queued behind another request. The corpus-wide
  commands wait for as long as they take: `sq migrate up`, `sq migrate repad`,
  `sq migrate rename-type`, `sq migrate rename-status`, `sq migrate rename-field`,
  `sq migrate rename-kind`, `sq repair`, `sq renumber` and `sq import`. After 10 seconds they print
  a line on stderr naming the operation, so a long run is not taken for a hang:

  ```
  waiting for the daemon (squad.repair)…
  warning: waiting for the index lock <path>…
  ```

  (the second line is the command's own notice, printed when the answer arrives). When the 300
  seconds pass, `sq` prints the message above with the duration
  (`… after 300 s; the operation may still complete. …`) and exits `1`.
- **Nothing is sent twice.** If the connection is lost after the command was sent, `sq` reports it
  (`error: the connection to the squad served at <endpoint> was lost after the request was sent;
  the operation may still complete. …`) and exits `1`. It never runs the command again, in either
  mode, because the first attempt may have been applied.

## Settings

The daemon is configured by a `[daemon]` table in `.squads.toml`. Every key is optional, and an
absent table means the defaults:

```toml
[daemon]
enabled = true              # false: local mode only; sq never starts or contacts a daemon
idle_timeout_minutes = 30   # the daemon exits after this long without a request; 0 = never
browser = false             # true: also open the browser listener (see Security)
```

`sq init` and `sq adopt` write no `[daemon]` table, and no `sq` command adds one: you write it.
`sq migrate up` keeps its values.

The environment variable **`SQUADS_DAEMON`** overrides `enabled` for every command run in that
environment:

| `SQUADS_DAEMON` | Effect |
|---|---|
| `off` | local mode, whatever `.squads.toml` says |
| `on` | the daemon is used, even where `enabled = false` |
| unset or empty | `enabled` decides |

The value is not case-sensitive. Use `SQUADS_DAEMON=off` to keep a test suite or a CI job that runs
`sq` in temporary squads in local mode, and `SQUADS_DAEMON=on` to try the daemon on a project
without committing a setting.

**A setting takes effect at the next command.** Changing `.squads.toml`, or any file under
`<squad-dir>/.overrides/`, retires the running daemon: the next command it receives is answered in
local mode, the daemon exits, and the command after that starts a daemon that reads the new
configuration. `sq override` and `sq migrate up`, which write those files, retire it the same way.

**An unusable setting means local mode.** A value of the wrong type (`enabled = "yes"`), an
`idle_timeout_minutes` that is negative or not a whole number, a `[daemon]` that is not a table, or
a `SQUADS_DAEMON` other than `on` or `off` puts every command in local mode. A command that
would otherwise go to the daemon prints the problem on stderr, then runs:

```
warning: SQUADS_DAEMON must be on or off, got 'maybe'; every command runs in local mode until it is fixed
```

`sq check` reports it too, and also an unknown key in the table, which is otherwise ignored:

```
warn .squads.toml: [daemon] enabled must be true or false, got 'yes'; every command runs in local mode until it is fixed
warn .squads.toml: [daemon] has an unknown key 'colour'; it is ignored
warn SQUADS_DAEMON: SQUADS_DAEMON must be on or off, got 'maybe'; every command runs in local mode until it is fixed
```

Local mode is always correct, so a broken setting only costs speed. The check is
`daemon_config_valid` ([overrides.md](overrides.md) lists the checks).

## Inspecting and stopping the daemon

You never need to start the daemon by hand. Two commands show and stop it:

```
$ sq daemon status
daemon running (pid 2562526)
  version: 0.19.0
  squad: /home/me/project/squads
  started: 2026-10-30T08:09:18+00:00
  exits idle at: 2026-10-30T08:29:23+00:00
  listening: /run/user/1000/squads/aebdaea5929e.sock (unix, cli)
  listening: 127.0.0.1:34973 (tcp, browser)
  listening: [::1]:34973 (tcp, browser)
  vocabulary: c24d19a05860b8f9834a4089039e8bd9fde8d6efe0eee382272699b8c2fec527
```

With no daemon running it prints `no daemon is running for this squad` and exits `0`.
`exits idle at` reads `never` when `idle_timeout_minutes = 0`. The `browser` lines appear only
when the browser listener is on. `sq daemon status --json` prints one object,
`{"running": …, "daemon": …}`, where `daemon` is the identity `GET /v1/daemon` returns (see
[api.md](api.md#the-daemons-own-routes)) or `null`.

`sq daemon stop` asks the daemon to exit once the request in progress has finished, waits until its
files are gone, and prints `daemon stopped`. With none running it prints
`no daemon is running for this squad` and exits `0`. `sq daemon stop --json` prints
`{"was_running": true}` or `{"was_running": false}`. Unless the daemon is disabled, the next
command starts a fresh one.

## Lifecycle

- **Start.** A command in remote mode that finds no daemon for its squad starts one in the
  background, detached from your terminal, and waits up to 5 seconds for it to be ready. If two
  commands start one at the same time, one daemon wins and both use it.
- **One daemon per squad and per installation.** A daemon is identified by the squad directory's
  real path, the squads version and the directory squads is installed in. A symlink, a `-C` path
  and a walk-up from a subfolder all reach the same daemon. Two installations, even of the same
  version, never share one, so upgrading squads starts a new daemon; the old one exits when it has
  been idle long enough.
- **Idle exit.** The daemon exits after `idle_timeout_minutes` without a request (30 by default).
  A request in progress counts as activity until it ends. With `0` it never exits by itself.
- **Retirement.** A changed `.squads.toml` or `.overrides/` file retires it, as described under
  [Settings](#settings).
- **Stale files.** A daemon that was killed leaves files behind. The next command notices that
  nothing answers on them and removes them before it starts a new daemon.
- **One request at a time.** The daemon runs commands and API requests one after the other, in
  the order they arrive. A command sent while a long migration runs waits for it.

## What the daemon keeps between commands

The daemon builds its command tree and loads the squad's configuration once, when it starts; a
change to that configuration retires it (see [Settings](#settings)). Between commands it also keeps
the result of parsing the squad's files: the index (`.squads.json`), the frontmatter of each item
file, and the check of the workflow override against the index. Each entry is keyed by the content
of the file it came from. Every command still reads the files, and reuses a kept result only when
the content it has just read is the content that result was parsed from. An edit made outside the
daemon, by a local-mode command, `git`, an editor or another tool, is therefore seen by the very
next command, whatever the file's timestamps say. Nothing kept is a source of truth: the files are,
and a write reads them again under the file lock.

## What the daemon keeps on your machine

The daemon writes nothing inside the squad or the project. Its files live in a per-user **runtime
directory**:

| Platform | Runtime directory |
|---|---|
| Linux, WSL2 | `$XDG_RUNTIME_DIR/squads/` |
| macOS | `$TMPDIR/squads/` |
| native Windows | `%LOCALAPPDATA%\squads\` |
| otherwise (the variable above is unset) | `$XDG_CACHE_HOME/squads/run/`, or `~/.cache/squads/run/` |

On POSIX the directory is created with mode `0700` and must be owned by you and closed to other
users. For each daemon it holds four files named after the daemon's key, a short hash:

| File | Holds |
|---|---|
| `<key>.sock` | the Unix socket the CLI connects to (POSIX only), mode `0600` |
| `<key>.json` | the daemon's pid, version, squad directory and listeners |
| `<key>.lock` | a lock held for the daemon's lifetime, released by the system when the process ends |
| `<key>.log` | the daemon's own log for its current lifetime |

A clean exit (idle, stop, retirement) removes all four. After a crash the log stays until the next
daemon for that squad starts, which replaces it. When a request fails with an internal error, the
message says the traceback is in this log.

**Dependencies.** Installing squads also installs the daemon's HTTP server, `starlette` and
`uvicorn`, which bring `h11` and `click`. Only the daemon loads them: neither `sq` sending a
command to the daemon nor a command run in local mode does.

**A development install should keep the daemon off.** A daemon runs the code it started with. If
you run squads from a source checkout (an editable install), a daemon started before you changed
the code keeps answering with the old code until it exits. Set `enabled = false` in that project's
`[daemon]` table, or `SQUADS_DAEMON=off` in your shell, or run `sq daemon stop` after each change.

## When the daemon cannot be used

A command falls back to local mode only before it has been sent, so nothing can run twice.

If a daemon cannot be started, because the process cannot be spawned, it reports a failure, it
does not answer within 5 seconds, or the runtime directory is unusable (missing and impossible to
create, owned by another user, open to other users, or a path too long for a socket), the command
runs in local mode and prints one line on stderr. For a runtime directory open to other users:

```
warning: the daemon could not be used (/run/user/1000/squads is accessible to other users (mode 0755)); running locally. Set SQUADS_DAEMON=off or `enabled = false` under [daemon] in .squads.toml to stop trying.
```

The same line, with `the daemon did not answer` as the reason, follows a daemon that is running
but cannot be connected to: the command tries to reach it again for up to 5 seconds, then runs in
local mode.

The next command tries again. A daemon that refuses to start for a reason in the squad itself,
such as a workflow override that does not load, names that reason; the command then reports the
same problem in local mode.

A command also runs in local mode, with nothing printed, when:

- a file the command names cannot be read (see
  [Files a command reads, and prompts](#files-a-command-reads-and-prompts)), or a `-C` directory
  cannot be entered, so that local mode reports it;
- the daemon is retiring: it answers without running the command, which then runs locally.

Once the command has been sent, it is never run again: a lost connection, a timeout and Ctrl-C end
with the error under [What differs between the modes](#what-differs-between-the-modes). The one
exception is a prompt: when the daemon stops between the question and your answer, nothing has been
written, and the command runs in local mode from the start.

## Client and daemon versions

The CLI and the terminal browser only reach a daemon of their own installation (see
[Lifecycle](#lifecycle)), which runs the same version and reads the same configuration. Another
client of the API must match the daemon on two counts, and is refused before anything runs when it
does not:

- **The schema version.** A client and a daemon at different schema versions refuse each other
  (`409 schema_mismatch`).
- **The workflow vocabulary.** A client that parses commands with the squad's vocabulary sends its
  hash; if its bundled `workflow.toml` or the project's `.overrides/workflow.toml` differ from the
  ones the daemon loaded, the call is refused (`409 vocabulary_mismatch`).

squads' own client of the API, which `sq ui` uses, words the refusals as follows:

```
error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. Install a squads release at schema v<B>, then re-run.
error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. The squad's server must be upgraded and the squad migrated (sq migrate up) before this client can use it.
error: this checkout's workflow vocabulary differs from the squad served at <endpoint> (<document> differs). Bring this checkout in line with the squad, by pulling its configuration or installing the squads version it runs, then re-run.
```

The first means the client is behind; the second that it is ahead. Neither refusal falls back to
local mode: a local run would answer with a vocabulary or a schema the squad does not hold. A result
shape that changes incompatibly ships as a schema change, so the schema check also covers the API's
result shapes; see [api.md](api.md#compatibility) and [stability.md](stability.md#the-http-api).

## Security

The daemon has no authentication. It assumes that whoever can reach it is you. Who can reach it
depends on the platform and on the browser listener:

- **Linux, macOS and WSL2, with the browser listener off (the default):** only your own user can
  read and write the squad through the daemon. The CLI reaches it over a Unix socket that only you
  can open.
- **Native Windows, in any configuration:** any local process or user can read and write the squad
  through the daemon while it runs. Windows has no such socket, so the CLI reaches the daemon over
  a loopback TCP port, which any local user can connect to.
- **Any platform with `browser = true`:** the same as Windows, through the browser listener.

The command lines `sq` sends are taken on the CLI listener only. The browser listener serves the
API and nothing else.

This is how the daemon is designed, not a defect. If it does not suit a machine, keep the browser
listener off and, on a shared Windows machine, the daemon disabled.

**Attacks from a web page are refused on every platform.** Every TCP listener binds to the
loopback address only (`127.0.0.1`, and `::1` for the browser listener), never to an address
another machine can reach, and admits a request only when:

- its `Host` header names that listener (`127.0.0.1:<port>`, `localhost:<port>` or `[::1]:<port>`),
  which defeats DNS rebinding;
- a write (any method other than `GET` and `HEAD`) is JSON (`Content-Type: application/json`) and
  carries the header `Squads-Client: 1`, which a page on another origin cannot send without a
  preflight request, and the daemon answers no preflight and sends no CORS header;
- on the browser listener, a write carries an `Origin` equal to the listener's own
  (`http://<the Host it was sent to>`);
- on the Windows CLI port, the request carries no `Origin` at all.

A `GET` or `HEAD` never changes anything. The daemon never reads a file whose path a client sends,
so a caller who reaches it reaches the squad and nothing else your user can read.

**The actor is a claim.** A client names the actor a write is recorded under (the CLI sends what
`--as` says), and the daemon does not verify it. The actor recorded on an item, a comment or a
reflog line through the daemon is therefore a claim, like the session ids the reflog records. See
[api.md](api.md#request-headers).

## Windows

On native Windows:

- the runtime directory is `%LOCALAPPDATA%\squads\`, and must be owned by you;
- the CLI reaches the daemon over a loopback port on `127.0.0.1` instead of a socket, and checks
  that the daemon answering on it is the one recorded in `<key>.json`, since a port can be reused
  by another program;
- that CLI port refuses any request that carries an `Origin` header, which browsers send and the
  CLI never does;
- the daemon is started detached, with no console window;
- any local user can reach the daemon (see [Security](#security)).
