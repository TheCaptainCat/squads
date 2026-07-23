# Writing a backend

Claude Code is *the first* supported agent backend, not the only possible one. A backend translates
a squad (its roles, skills, and the workflow) into whatever config a given agent tool understands.
The rest of squads — items, the index, IDs, markers, workflows — is backend-agnostic.

## The contract

A backend implements the `AgentBackend` ABC (`squads._backends._base`):

```python
class AgentBackend(ABC):
    name: str
    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]: ...
    async def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]: ...
    async def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact: ...
    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact: ...
    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None: ...
    def managed_paths(self, ctx: BackendContext) -> list[str]: ...
```

- **`ensure_scaffold`** — create the tool's directories and base config (idempotent; never clobber
  user content). Claude Code makes `.claude/{agents,skills}` and merges `settings.json`.
- **`write_managed`** — (re)write the version/roster-dependent files: the general skill, the
  per-item-type skills, and any "project guidance" doc. Called by `init`/`adopt`/`sync`.
- **`generate_role_entry`** / **`generate_skill_entry`** — emit the per-role / per-skill entry (a
  file or a section, depending on the backend).
- **`remove_artifacts`** — delete the files for a removed role/skill.
- **`managed_paths`** — the root-relative paths this backend owns, read-only, for `sq check` to
  verify scaffolding is present (a presence check, not a currency/drift check).

`BackendContext` carries the resolved `SquadPaths` and helpers (each backend computes its own
`.claude/`-equivalent directory internally — there's no shared `claude_dir` on `SquadPaths`):

- `ctx.paths` — `squad_dir`, `root`, …
- `ctx.rel(path)` — project-root-relative, forward-slash path (for references and `Artifact` paths)
- `ctx.root_relative(item)` — the same for an item's markdown file

Each method returns `Artifact(path, kind, backend)` records (informational; the path is
root-relative).

## The recommended shape: pointers, not copies

Follow the Claude Code pattern: keep the **real, durable content under the squad folder** and write
**thin pointers** in the tool's config that reference it. ClaudeCodeBackend writes a role's real
definition to `squads/agents/roles/ROLE-*.md` and a pointer to `.claude/agents/<slug>.md` that
`@`-imports it; managed skill bodies live in `squads/agents/skills/<name>.md` with a pointer in
`.claude/skills/<name>/SKILL.md`. This keeps the "`.claude/` is pointers" invariant and means the
content survives even if the backend config is regenerated. The `_interactions` playbook
(`skills_for_role`, `PLAYBOOK`) tells you which skills a role gets and what each item skill should
say — reuse it.

## Registering one

Backends self-register. To add, say, a `cursor` backend:

1. Create `squads/_backends/_cursor/__init__.py` and `_cursor.py`:
   ```python
   # _cursor.py
   from squads._backends._base import AgentBackend, Artifact, BackendContext, RoleView
   from squads._models._item import Item
   from squads._roles._catalog import RoleDef

   class CursorBackend(AgentBackend):
       name = "cursor"
       async def ensure_scaffold(self, ctx): ...
       # … implement the rest …
   ```
   ```python
   # __init__.py  — register on import (side effect)
   from squads._backends._registry import register
   from squads._backends._cursor._cursor import CursorBackend
   register(CursorBackend)
   ```
2. Make `get_backend` discover it. Today `_registry.get_backend` imports the built-in
   `_claude_code` package for its registration side-effect; add an import for your package the same
   way (or generalize discovery if you add several).
3. Select it: `sq init --backend cursor` (stored in `active_backends` in `.squads.toml`;
   `--backend` is repeatable to run several backends side by side).

## Contract notes

- **Idempotent.** `ensure_scaffold`/`write_managed` run on every `init`/`adopt`/`sync` — never
  destroy user edits; merge where a file may already exist (see `_merge_settings`).
- **Versioned.** `sq sync` regenerates everything to the current version and stamps `.squads.toml`;
  any command nudges the user to sync when the installed version is newer.
- **Stay in your lane.** A backend only writes tool config / pointers — it never owns item content
  (that's the `.md` frontmatter + body). Nothing outside a backend should touch the tool's config
  directory.
