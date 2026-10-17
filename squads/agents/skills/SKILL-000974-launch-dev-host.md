---
id: SKILL-974
sequence_id: 974
type: skill
title: Launch dev host
status: Active
author: launch-dev-host
refs:
- ROLE-1:scopes
- ROLE-426:scopes
- ROLE-5:scopes
description: Open a VS Code Extension Development Host from WSL for the operator to
  see a client change.
created_at: '2026-09-29T14:09:09Z'
updated_at: '2026-09-29T14:09:27Z'
extra:
  slug: launch-dev-host
  description: Open a VS Code Extension Development Host from WSL for the operator
    to see a client change.
  when_to_use: When the operator needs to see a VS Code client change in a dev host,
    or a dev-host launch fails.
  allowed_tools: ''
---
<!-- sq:body -->
# Launch the VS Code dev host

How to open an Extension Development Host for the VS Code client (`clients/vscode`) from a WSL
session, so the operator can see a change on the Windows desktop. Only the operator can see the
window: launch once, then ask them what they see. Don't keep launching windows to find out.

## 1. Prefer F5

From a **WSL** VS Code window on the repo, pick **Run → "Run squads extension"** (F5). The repo's
`.vscode/launch.json` and `tasks.json` compile first and pass the right flags. There are no
path-translation or CLI-flavour traps on this route. It fails only when the folder is already open
in the operator's working window. That's when you use step 2.

## 2. From the CLI

Copy this command as it is:

```bash
cd clients/vscode && npm run compile     # later compiles: Ctrl+R in the host
code --new-window \
  --extensionDevelopmentPath=/home/pchat/projects/squads/clients/vscode \
  --disable-extension=pierre-chat.squads-vscode \
  /home/pchat/projects/squads
```

Each of these breaks the launch, and each has been confirmed by a wasted attempt:

- **Use bare `code`, which is Windows stable, even though the operator works in Insiders.**
  - `code-insiders` on the session's PATH is the remote-cli stub. It prints
    `Ignoring option 'extensionDevelopmentPath'` and exits 0 without opening a dev host.
  - The Windows Insiders launcher accepts the flags. It worked once, but it force-updated the
    WSL server and never worked again.
  - After every launch, read the output for `Ignoring option`. An exit code of 0 proves nothing.
- **Use raw Linux paths** (`/home/pchat/...`). Never use the `wslpath -w` UNC form
  (`\\wsl.localhost\...`): Windows then treats the folder as foreign and asks for the WSL extension.
- **Disable only the installed extension** (`--disable-extension=pierre-chat.squads-vscode`), not
  every extension (`--disable-extensions`).
  - The blanket form also disables Remote-WSL. The host then runs on Windows, where the Linux `sq`
    can't execute, and every view comes up empty.
  - The targeted form still avoids the duplicate-command collision with the installed extension.
- **Don't pass `--remote wsl+<distro>`.** The Windows wrapper adds it itself.
- **Don't use the Linux VS Code under `.vscode-test/` through WSLg.** It renders badly and can't
  answer a visual question. The operator's Windows host is the authoritative visual check.

To confirm a dev host is really up, look for `--extensionDevelopmentPath` in a live process's
`/proc/<pid>/cmdline`. Avoid a broad `pkill -f extensionDevelopmentPath`: it also matches your own
command line.

## 3. Which `sq` the host runs

The operator's WSL machine settings set `squads.sqPath` to the released uv tool
(`~/.local/bin/sq`). That setting beats every discovery strategy, and the dev host inherits it.
**By default the dev host runs the released `sq`, not the dev build.**

To see an engine change through the dev host:

- Open a scratch squad instead of the repo, as the host's folder argument.
- Give that folder a `.vscode/settings.json` with
  `"squads.sqPath": "/home/pchat/projects/squads/.venv/bin/sq"`.
- Never put a personal absolute path in the repo's committed `.vscode/settings.json`.

## 4. When a dev is working in `clients/vscode/`

- Pin a git worktree at the commit under test and point `--extensionDevelopmentPath` there.
  Otherwise the check runs against half-edited files, and a mid-edit `package.json` stops the
  extension from loading at all.
- Never stash, reset or check out in the shared tree to get a clean state.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
