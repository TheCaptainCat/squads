"""agents_md backend: writes/refreshes a single AGENTS.md at the project root.

Per-role and per-skill entries are staged as individual files under
``.agents_md/roles/`` and ``.agents_md/skills/`` so ``generate_role_entry`` and
``generate_skill_entry`` satisfy the Artifact contract (one file per item, removable).
``write_managed`` then reads those staging files to compile the full AGENTS.md that
non-Claude agent tools actually consume: roster, workflow cheatsheet, and per-role
mission text all in one place.  If the staging directory is absent (e.g. in unit
tests that call ``write_managed`` directly), role definitions fall back to name/title
only and the workflow section is still included.
"""

from pathlib import Path

from squads import _aio
from squads._backends._agents_md import _managed as managed
from squads._backends._base import AgentBackend, Artifact, BackendContext, OperatorView, RoleView
from squads._models._enums import TYPE_ALIASES, ItemType
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef

_AGENTS_MD = "AGENTS.md"
_STAGING_DIR = ".agents_md"
_ROLES_DIR = "roles"
_SKILLS_DIR = "skills"


async def _read_staging_role(staging_dir: Path, slug: str) -> dict[str, object]:
    """Read cached role data from a staging file written by ``generate_role_entry``.

    Returns a dict with ``mission`` and ``responsibilities`` keys.  Both default to
    empty values when the staging file is absent (backward-compatible fallback).
    """
    role_file = staging_dir / _ROLES_DIR / f"{slug}.md"
    if not await _aio.path_exists(role_file):
        return {"mission": "", "responsibilities": []}
    # Parse the simple key: value lines written by role_entry.md.j2.
    mission = ""
    for line in (await _aio.read_text(role_file)).splitlines():
        if line.startswith("**Mission:**"):
            mission = line.removeprefix("**Mission:**").strip()
            break
    return {"mission": mission, "responsibilities": []}


class AgentsMdBackend(AgentBackend):
    name = "agents_md"

    # ------------------------------------------------------------------ scaffold

    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        """Ensure AGENTS.md exists at the project root (never clobber user content)."""
        agents_md = ctx.root / _AGENTS_MD
        if not await _aio.path_exists(agents_md):
            await _aio.write_text(
                agents_md,
                "# AGENTS.md — Project AI agent guidance\n\n"
                "_Run `sq sync` to populate this file with your squad's roster and workflow._\n",
            )
        return [Artifact(ctx.rel(agents_md), "config", self.name)]

    # ------------------------------------------------------------------ managed files

    async def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]:
        """Compile roster, workflow cheatsheet, and role missions into AGENTS.md.

        Role mission text is read from the per-role staging files written by
        ``generate_role_entry`` (under ``.agents_md/roles/``).  When a staging file is
        absent the role entry falls back to name/title-only — the workflow section is
        always included regardless.
        """
        squad_dir = ctx.paths.config.squad_dir
        staging_dir = ctx.root / _STAGING_DIR
        roles_data = [
            {
                "full_name": r.full_name,
                "title": r.title,
                "slug": r.slug,
                **(await _read_staging_role(staging_dir, r.slug)),
            }
            for r in roster
        ]
        section = render(
            "agents_md/agents_section.md.j2",
            squad_dir=squad_dir,
            roles=roles_data,
            operators=[{"full_name": o.full_name, "slug": o.slug} for o in operators],
            type_aliases=TYPE_ALIASES,
        )
        agents_md = ctx.root / _AGENTS_MD
        await managed.inject(agents_md, section)
        return [Artifact(ctx.rel(agents_md), "config", self.name)]

    # ------------------------------------------------------------------ entries

    async def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        """Write a per-role staging file under .agents_md/roles/.

        These files are consumed by ``write_managed`` when it compiles the Role
        definitions section of AGENTS.md.
        """
        staging = ctx.root / _STAGING_DIR / _ROLES_DIR
        await _aio.mkdir(staging, parents=True, exist_ok=True)
        entry_file = staging / f"{role.slug}.md"
        await _aio.write_text(
            entry_file,
            render(
                "agents_md/role_entry.md.j2",
                slug=role.slug,
                full_name=role.full_name,
                role_title=role.title,
                mission=role.mission,
                squad_path=ctx.root_relative(item),
            ),
        )
        return Artifact(ctx.rel(entry_file), "role_entry", self.name)

    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        """Write a per-skill staging file under .agents_md/skills/."""
        slug = item.extra.get(X.SLUG, item.slug)
        description = item.extra.get(X.DESCRIPTION) or item.description or item.title
        staging = ctx.root / _STAGING_DIR / _SKILLS_DIR
        await _aio.mkdir(staging, parents=True, exist_ok=True)
        entry_file = staging / f"{slug}.md"
        await _aio.write_text(
            entry_file,
            render(
                "agents_md/skill_entry.md.j2",
                slug=slug,
                description=description,
                squad_path=ctx.root_relative(item),
            ),
        )
        return Artifact(ctx.rel(entry_file), "skill_entry", self.name)

    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        """Remove the per-item staging file for a role or skill (missing_ok semantics)."""
        slug = item.extra.get(X.SLUG, item.slug)
        if item.type is ItemType.SKILL:
            await _aio.path_unlink(
                ctx.root / _STAGING_DIR / _SKILLS_DIR / f"{slug}.md", missing_ok=True
            )
        else:
            await _aio.path_unlink(
                ctx.root / _STAGING_DIR / _ROLES_DIR / f"{slug}.md", missing_ok=True
            )

    def managed_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative paths owned by this backend (present-only check; read-only)."""
        return [ctx.rel(ctx.root / _AGENTS_MD)]
