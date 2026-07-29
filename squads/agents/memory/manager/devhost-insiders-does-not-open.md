---
summary: Dev host opens from the Windows STABLE code launcher; the Insiders launcher
  silently fails. Cause unknown.
created_at: '2026-07-29T12:46:33Z'
---
Dev host opens from the Windows STABLE code launcher; the Insiders launcher silently fails. Cause unknown.

Pierre asked for `code-insiders` (he works in Insiders). It does not work for an Extension
Development Host from WSL, and this supersedes the earlier note asking for it.

What was tried, all exiting 0 with an empty log and no window:
- `code-insiders` on PATH — that resolves to the remote-cli shim inside `.vscode-server-insiders`,
  which prints "Ignoring option 'extensionDevelopmentPath': not supported" and does nothing.
- The Windows launcher at `/mnt/c/Users/<user>/AppData/Local/Programs/Microsoft VS Code Insiders/bin/code-insiders`,
  with `--remote wsl+$DISTRO`, with the repo as workspace. This worked exactly ONCE — the
  invocation that also had to install a new WSL server build — and never again.
- The same launcher without `--remote` (lets the WSL shim supply it).
- The same launcher pointed at a git worktree as its own workspace, to rule out colliding with the
  folder already open in Pierre's editor. That hypothesis was wrong; it also failed.

The Windows **stable** launcher (`code`, which is what bare `code` resolves to on PATH) opens a dev
host reliably, including against the same worktree and the same flags. Use it until the Insiders
failure is understood. Do not keep firing launchers at Pierre's desktop to find out — ask him what
he sees instead; only he can observe the window.

Side effect worth knowing: the one Insiders launch that worked force-updated the WSL server and
deleted the build the live session was running on. The session survived (Linux keeps unlinked files
open) but a window reload reconnects to the new build. Related: [[vscode-devhost-launch-method]].