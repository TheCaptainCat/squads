# The daemon

squads can keep one long-lived process per squad, the **daemon**, that serves the squad over a
local HTTP API. The CLI uses it to answer commands without rebuilding everything on every
invocation, and any other client (the terminal browser, a script, a web front) can call the same
API. This page covers how the CLI uses the daemon, how to configure and inspect it, what it keeps
on your machine, and who can reach it. The API itself is described in [api.md](api.md).

## Remote mode and local mode

Each `sq` command runs in one of two modes, chosen once when it starts:

- **Remote mode.** The command is answered by the squad's daemon. If none is running, the command
  starts one and waits for it. Later commands find the same daemon.
- **Local mode.** The command reads and writes the squad files itself, in its own process, as
  squads always has.

The CLI parses your command line and prints the result in your own process in both modes, so the
output and the exit code are the same, `--json` included. A write made in one mode is visible to a
command in the other mode straight away: the daemon keeps nothing about the squad between two
requests, and it takes the same file lock as a local command.

Remote mode applies when the daemon is enabled (it is by default, see
[Settings](#settings)). Local mode applies when it is disabled, and when a daemon cannot be started
(see [When the daemon cannot be used](#when-the-daemon-cannot-be-used)).

These commands never start or contact a daemon, whatever the settings: `sq --help`, `sq --version`,
shell completion, `sq docs`, `sq migrate help`, `sq migrate chlog`, `sq init`, `sq adopt` and
`sq daemon`. `sq ui` follows the same rule as the other commands.

### What differs between the modes

The output is the same; the timing and Ctrl-C are not.

- **Output arrives when the operation ends.** A remote command prints nothing until the daemon
  answers. A notice raised while the operation runs, such as
  `warning: waiting for the index lock <path>…`, is printed when the answer arrives, before the
  result. In local mode it is printed as it happens. The lines are the same.
- **Ctrl-C ends the wait, not the operation.** In remote mode, Ctrl-C stops the command waiting for
  the daemon. An operation the daemon has already started runs to completion, so a write may still
  be applied. The command prints

  ```
  error: no answer from the squad served at <endpoint>; the operation may still complete. Check its result before running it again.
  ```

  and exits `130`. Check the result (with `show`, `list` or `sq reflog`) before running the command
  again. In local mode, Ctrl-C ends the process.
- **Timeouts.** A remote command waits at most 5 seconds to connect to the daemon, and at most 300
  seconds for its answer, including any time spent queued behind another request. The corpus-wide
  operations wait for as long as they take: `sq migrate up`, `sq migrate repad`,
  `sq migrate rename-type`, `sq migrate rename-status`, `sq migrate rename-field`,
  `sq migrate rename-kind`, `sq repair`, `sq renumber` and `sq import`. After 10 seconds they print
  `waiting for the daemon (<operation>)…` on stderr, so a long run is not taken for a hang. When
  the 300 seconds pass, the command prints the message above with the duration
  (`… after 300 s; the operation may still complete. …`) and exits `1`.
- **Nothing is sent twice.** If the connection is lost after the request was sent, the command
  reports it (`error: the connection to the squad served at <endpoint> was lost after the request
  was sent (…); the operation may still complete. …`) and exits `1`. It never runs the operation
  again, in either mode, because the first attempt may have been applied.

A connection that cannot be made at all (nothing was sent) is handled like a daemon that cannot be
started: the command runs in local mode.

Prompts, such as the confirmation before a removal, are asked in your own terminal in both modes.

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
a `SQUADS_DAEMON` other than `on` or `off` puts every command in local mode, with one line on stderr
naming the problem. `sq check` reports the same problems, and also an unknown key in the table,
which is otherwise ignored:

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
- **One request at a time.** The daemon runs operations one after the other, in the order they
  arrive. A command sent while a long migration runs waits for it.

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
`uvicorn`, which bring `h11` and `click`. Only the daemon loads them; a command in either mode does
not.

**A development install should keep the daemon off.** A daemon runs the code it started with. If
you run squads from a source checkout (an editable install), a daemon started before you changed
the code keeps answering with the old code until it exits. Set `enabled = false` in that project's
`[daemon]` table, or `SQUADS_DAEMON=off` in your shell, or run `sq daemon stop` after each change.

## When the daemon cannot be used

If a daemon cannot be started, because the process cannot be spawned, it reports a failure, it
does not answer within 5 seconds, or the runtime directory is unusable (missing and impossible to
create, owned by another user, open to other users, or a path too long for a socket), the command
runs in local mode and prints one line on stderr:

```
warning: the daemon could not be used (<reason>); running locally. Set SQUADS_DAEMON=off or `enabled = false` under [daemon] in .squads.toml to stop trying.
```

The next command tries again. A daemon that refuses to start for a reason in the squad itself,
such as a workflow override that does not load, names that reason; the command then reports the
same problem in local mode.

A daemon that is retiring answers a command without running it, and the command runs in local
mode with nothing printed. This is the only case where a command is handed to local mode after
reaching the daemon.

## Client and daemon versions

The CLI and its daemon come from the same installation, so they always agree. Another client, or
a client reaching a squad served from another installation, must match the daemon on two counts,
and is refused before anything runs when it does not:

- **The schema version.** A client and a daemon at different schema versions refuse each other.
  The CLI prints one of two messages and exits `1`:

  ```
  error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. Install a squads release at schema v<B>, then re-run.
  error: squads <version> speaks schema v<A>, and the squad served at <endpoint> runs schema v<B>. The squad's server must be upgraded and the squad migrated (sq migrate up) before this client can use it.
  ```

  The first means the client is behind; the second that it is ahead.
- **The workflow vocabulary.** The CLI parses your command with the vocabulary of its own checkout:
  its bundled `workflow.toml` and the project's `.overrides/workflow.toml`. If those differ from
  the ones the daemon loaded, the call is refused:

  ```
  error: this checkout's workflow vocabulary differs from the squad served at <endpoint> (<document> differs). Bring this checkout in line with the squad, by pulling its configuration or installing the squads version it runs, then re-run.
  ```

Neither refusal falls back to local mode: a local run would answer with a vocabulary or a schema
the squad does not hold. A result shape that changes incompatibly ships as a schema change, so the
schema check also covers the API's result shapes; see [stability.md](stability.md#the-http-api).

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
