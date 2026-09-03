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
    async def candidate_orphans(
        self, ctx: BackendContext, roster: list[RoleView], skill_slugs: set[str]
    ) -> list[str]: ...
    def managed_paths(self, ctx: BackendContext) -> list[str]: ...
```

That is the whole ABC — seven methods, and it does not grow.

- **`ensure_scaffold`** — create the tool's directories and base config (idempotent; never clobber
  user content). Claude Code makes `.claude/{agents,skills}` and merges `settings.json`.
- **`write_managed`** — (re)write the version/roster-dependent files: the general skill, the
  per-item-type skills, and any "project guidance" doc. Called by `init`/`adopt`/`sync`.
- **`generate_role_entry`** / **`generate_skill_entry`** — emit the per-role / per-skill entry (a
  file or a section, depending on the backend).
- **`remove_artifacts`** — delete the files for a removed role/skill. This is also what withdraws a
  *retired* entry's files — see "Status is not your concern" below.
- **`candidate_orphans`** — report, read-only, the on-disk pointer/skill files this backend does
  **not** manage: present on disk but naming no slug in the roster and none in the known-skill
  vocabulary. Warn-only candidates for `sq init` / `sq adopt` to print. Never delete, move, or
  rewrite anything here, and don't report a slug you *do* manage just because this particular
  invocation didn't happen to rewrite its file.
- **`managed_paths`** — the root-relative paths this backend owns, read-only, for `sq check` to
  verify scaffolding is present (a presence check, not a currency/drift check).

Two more methods are non-abstract, with a working default — they don't grow the seven above (a
subclass implementing only the seven still instantiates), but a bundled backend overrides them to
answer question 4 and question 5 below:

- **`restriction_fragment(role)`** — pure, synchronous: the exact substring this backend's
  rendered role entry carries when the role's capability boundary currently applies, or `None`.
  Used to key `sq check`'s currency severity to the containment rule instead of a hard-coded field
  name — see "Detection: presence and currency" below.
- **`render_role_entry`/`render_skill_entry`** — the pure render of what
  `generate_role_entry`/`generate_skill_entry` would write, without writing it. `None` when this
  backend has no per-entry file for that kind.

## The five per-host questions

A generated pointer materialises only what its host needs before an agent can act, plus the
commands that fetch the rest — never a local path, never more state than a containment rule
allows. That rule is universal: a value belongs in the pointer only when the host consumes it at
or before spawn **and** a runtime fetch cannot substitute for its effect (it *restricts* or
*configures* the session, rather than merely *supplying* content). What is **not** universal is
each host's *answer*, so a new backend answers five questions from its own host's documentation
alone — no reading of squads internals required:

1. **Can an agent running under this host execute a command at all?** `True`, `False`, or "not
   knowably" — the normal condition for a backend whose target host's command capability is
   declared by whoever builds it, not by us.
2. **Which of the values squads projects does this host's configuration have a place for?** The
   expressible set. A value squads projects that this host cannot express is reported once, at
   write time, and dropped — never silently, and never re-validated a second time at storage time
   (`ClaudeCodeBackend`'s `_VALID_MODELS`/`model_drop_warning` is the worked example for one
   field).
3. **Which of those must be present for this host to find and dispatch an entry at all?** The
   irreducible set, from the host's own discovery contract.
4. **Which of those constrain what the session may do, rather than configure how it runs?** The
   capability boundary — `restriction_fragment`.
5. **What would you write for this entry, without writing it?** The pure render —
   `render_role_entry`/`render_skill_entry` — that the currency check below compares against disk.

`ClaudeCodeBackend` and `AgentsMdBackend` each answer all five explicitly at their own class
docstring — read those for two worked examples, including why they differ (a host that can run
`sq` fetches its definition; a host that cannot keeps compiled prose instead).

## Detection: presence and currency

`sq check` reports two findings over the same declared-path widening
(`managed_entry_paths`/`managed_paths`), scoped to the roster's currently **live** entries:

- **Presence** — does a declared path exist. Reported at error for a backend's fixed top-level
  files (`managed_paths`), at warn for a per-entry pointer (`managed_entry_paths`).
- **Currency** — does an existing per-entry pointer's content match a fresh render right now
  (question 5). A drifted or missing capability restriction (question 4) is an **error** — a stale
  pointer still granting authority the squad revoked is a live capability escalation, unrepairable
  from inside the session it governs; any other content drift is a **warn**. A correct,
  already-current pointer produces no finding.

Both are cross-source (they compare the index against the disk), so both go through `sq check`'s
one confirm round rather than being reported straight off the scan — a mutation racing the check
(most commonly a retirement withdrawing the very pointer being checked) resolves rather than
producing a false positive. `sq sync` reports what it regenerated for each, worded "was missing"
or "had drifted" so an operator can tell the two facts about their repository apart.

`BackendContext` carries the resolved `SquadPaths` and helpers (each backend computes its own
`.claude/`-equivalent directory internally — there's no shared `claude_dir` on `SquadPaths`):

- `ctx.paths` — `squad_dir`, `root`, …
- `ctx.rel(path)` — project-root-relative, forward-slash path (for references and `Artifact` paths)
- `ctx.root_relative(item)` — the same for an item's markdown file

The **writing** methods return `Artifact(path, kind, backend)` records — informational, with a
root-relative path. The read-only reporters (`candidate_orphans`, `managed_paths`) return plain
root-relative path strings, and `remove_artifacts` returns nothing.

### Status is not your concern

No ABC method takes or returns a status, and no backend ever sees one. squads decides whether a
roster entry is materialised (its status is live) or withdrawn (it isn't), and expresses withdrawal
through `remove_artifacts` plus recompiling the managed region that listed the entry. Implement the
seven methods above and you inherit that behaviour — do **not** add a status branch or a
`withdraw_artifacts` method of your own.

## The recommended shape: pointers, not copies

Follow the Claude Code pattern: keep the **real, durable content under the squad folder** and write
**thin pointers** in the tool's config that name the command to fetch it — never a local path (see
"The five per-host questions" below). ClaudeCodeBackend writes a role's real definition to
`squads/agents/roles/ROLE-*.md` and a pointer to `.claude/agents/<slug>.md` that names `sq role
<slug> show`; managed skill bodies live in `squads/agents/skills/<name>.md` with a pointer in
`.claude/skills/<name>/SKILL.md` naming `sq skill <slug> show`. This keeps the "`.claude/` is
pointers" invariant and means the content survives even if the backend config is regenerated. The
`_interactions` playbook
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
