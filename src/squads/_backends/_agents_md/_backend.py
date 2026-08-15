"""agents_md backend: writes/refreshes a single AGENTS.md at the project root.

Per-role and per-skill entries are staged as individual files under
``.agents_md/roles/`` and ``.agents_md/skills/`` so ``generate_role_entry`` and
``generate_skill_entry`` satisfy the Artifact contract (one file per item, removable).
``write_managed`` then compiles the full AGENTS.md that non-Claude agent tools actually
consume: roster, workflow cheatsheet, and per-role mission/responsibilities all in one
place.  It builds that entirely from the ``RoleView``s it is passed — the staging files are
write-only artifacts, never an input, so this backend never reads back its own output.
"""

from squads import _aio
from squads._backends._agents_md import _managed as managed
from squads._backends._base import AgentBackend, Artifact, BackendContext, OperatorView, RoleView
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._workflow import ROSTER_SKILL
from squads._workflow._models import WorkflowSpec

_AGENTS_MD = "AGENTS.md"
_STAGING_DIR = ".agents_md"
_ROLES_DIR = "roles"
_SKILLS_DIR = "skills"


def _also_creatable_types(spec: WorkflowSpec, anchor_type: str | None) -> str:
    """The ``# also: ...`` list on the ``sq create <anchor>`` example line — every other
    non-roster type the active spec declares, in its own display order, never a hardcoded
    bundled list: a dropped type simply does not appear, and a renamed one appears under its
    new name, with nothing left pointing at the old one.

    ``anchor_type`` is the same generically-derived (:func:`interactions.cheatsheet_anchor_type`)
    type the ``sq create`` example line itself is built from — excluded here so it isn't listed
    against itself, whatever it happens to be (no longer hardcoded to ``"task"``)."""
    others = sorted(
        (t for t, ts in spec.items.items() if t != anchor_type and ts.category != "roster"),
        key=lambda t: (spec.items[t].order, t),
    )
    return "|".join(others)


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
        """Compile roster, workflow cheatsheet, and role missions/responsibilities into AGENTS.md.

        Every role field rendered here comes from the ``RoleView``s the service passes in.
        The staging files under ``.agents_md/roles/`` are output only — one file per role so
        ``generate_role_entry`` satisfies the Artifact contract — and are never read back.

        They used to be: ``RoleView`` carried no ``mission``, so this method recovered it by
        matching the literal ``**Mission:**`` prefix on a line of the markdown
        ``generate_role_entry`` had just rendered from ``role_entry.md.j2``. That made a
        template's formatting the carrier of a declaration — relabel the line and every
        mission vanished from the compiled file, with nothing reporting it — and it never
        recovered ``responsibilities`` at all: that key came back as an unconditional empty
        list, so the section template's responsibilities block was dead code that had never
        rendered once. Both fields are now declared on the view.
        """
        squad_dir = ctx.paths.config.squad_dir
        roles_data = [
            {
                "full_name": r.full_name,
                "title": r.title,
                "slug": r.slug,
                "mission": r.mission,
                "responsibilities": list(r.responsibilities),
            }
            for r in roster
        ]
        from squads import _interactions as interactions
        from squads._workflow import bundled_spec

        spec = ctx.spec if ctx.spec is not None else bundled_spec()
        anchor_ctx = interactions.cheatsheet_anchor_context(spec)
        section = render(
            "agents_md/agents_section.md.j2",
            squad_dir=squad_dir,
            roles=roles_data,
            operators=[{"full_name": o.full_name, "slug": o.slug} for o in operators],
            spec=spec,
            # The ACTIVE (merged) playbook, so the included cheatsheet's authoring bullets
            # resolve an override-declared authoring role rather than the bundled lanes only.
            playbook=ctx.playbook,
            also_creatable_types=_also_creatable_types(spec, anchor_ctx["anchor"]),
            **anchor_ctx,
        )
        agents_md = ctx.root / _AGENTS_MD
        contradiction = await managed.inject(agents_md, section)
        warning = (
            f"{ctx.rel(agents_md)} had pre-existing hand-written content with no squads "
            "markers; the managed section was inserted at the top — review it for possible "
            "contradiction with that content."
            if contradiction
            else None
        )
        return [Artifact(ctx.rel(agents_md), "config", self.name, warning=warning)]

    # ------------------------------------------------------------------ entries

    async def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        """Write a per-role staging file under .agents_md/roles/.

        Output only: one file per role so this method has an Artifact to name and
        ``remove_artifacts`` has something to delete. ``write_managed`` compiles AGENTS.md
        from the ``RoleView`` roster it is handed, never from these files, so editing this
        template changes the staged entry alone and can no longer empty a field out of the
        compiled section.
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
                skills=ctx.resolved_skills_for(role.slug),
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
        if item.type == ROSTER_SKILL:
            await _aio.path_unlink(
                ctx.root / _STAGING_DIR / _SKILLS_DIR / f"{slug}.md", missing_ok=True
            )
        else:
            await _aio.path_unlink(
                ctx.root / _STAGING_DIR / _ROLES_DIR / f"{slug}.md", missing_ok=True
            )

    async def candidate_orphans(
        self, ctx: BackendContext, roster: list[RoleView], skill_slugs: set[str]
    ) -> list[str]:
        """Every ``.agents_md/roles/*.md``/``.agents_md/skills/*.md`` staging file on disk
        whose slug matches no active role/skill — see the ABC docstring for the semantics."""
        known_roles = {r.slug for r in roster}
        staging = ctx.root / _STAGING_DIR
        orphans: list[str] = []

        roles_dir = staging / _ROLES_DIR
        if await _aio.path_exists(roles_dir):
            paths = await _aio.to_thread(lambda: sorted(roles_dir.glob("*.md")))
            orphans += [ctx.rel(p) for p in paths if p.stem not in known_roles]

        skills_dir = staging / _SKILLS_DIR
        if await _aio.path_exists(skills_dir):
            paths = await _aio.to_thread(lambda: sorted(skills_dir.glob("*.md")))
            orphans += [ctx.rel(p) for p in paths if p.stem not in skill_slugs]
        return orphans

    def managed_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative paths owned by this backend (present-only check; read-only)."""
        return [ctx.rel(ctx.root / _AGENTS_MD)]
