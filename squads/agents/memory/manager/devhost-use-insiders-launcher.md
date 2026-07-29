---
summary: Launch the dev host with code-insiders, derived from the session's own server
  dir — bare 'code' is stable and the wrong app.
created_at: '2026-07-29T09:23:57Z'
---
Launch the dev host with code-insiders, derived from the session's own server dir — bare 'code' is stable and the wrong app.

Pierre works in VS Code Insiders. Bare `code` on PATH resolves to stable
(`/mnt/c/Program Files/Microsoft VS Code/bin/code`) no matter which flavour hosts the session,
so launching with it opens a second, different application alongside the one he is using.

Detect the flavour instead of assuming it. Three independent signals, all present in the session
environment: `$VSCODE_GIT_ASKPASS_NODE` contains the server directory
(`.vscode-server-insiders` vs `.vscode-server`); the remote CLI on PATH is
`~/.vscode-server-insiders/bin/<hash>/bin/remote-cli/code-insiders`; and `TERM_PROGRAM=vscode`
confirms the VS Code family at all (a Cursor or Windsurf session differs here).

Launch shape that works on WSL: `code-insiders --remote wsl+$WSL_DISTRO_NAME <repo>
--extensionDevelopmentPath=<ext dir> --new-window`. Leave `--disable-extensions` off — it
disables Remote-WSL, the host then runs on Windows over the UNC share, and the Linux `sq` in
`.venv/bin` cannot execute, so discovery fails and you inspect an error instead of the feature.
Recompile first. When a dev is live in the extension tree, pin a git worktree at the commit under
test and point `--extensionDevelopmentPath` at that, so the visual check is not a moving target.