---
summary: 'Dev host: follow the launch-dev-host skill; don''t reconstruct the launch
  from memory.'
created_at: '2026-09-29T14:08:17Z'
---
Follow the `launch-dev-host` skill (`sq skill launch-dev-host show`); it holds the recipe. The traps, in short:
- Prefer F5.
- On the CLI, use bare stable `code`: the Insiders stub silently ignores the dev flags.
- Use raw Linux paths.
- Disable only the installed extension, not every extension.
- Machine settings pin `squads.sqPath` to the released uv tool, so an engine change needs a scratch folder whose settings point at the `.venv` sq.

Launch once and ask the operator what they see: only they can see the window.