"""agents_md backend: writes/refreshes a single AGENTS.md at the project root.

``write_managed`` compiles the whole file (roster, workflow cheatsheet, per-role
mission/responsibilities) from the ``RoleView``s/``OperatorView``s it is passed.
``generate_role_entry``/``generate_skill_entry`` write nothing: they satisfy the
``AgentBackend`` ABC, and an external agent tool reads ``AGENTS.md`` itself, so there is no
per-entry file to discover.

Both of them, and ``remove_artifacts``, delete a leftover ``.agents_md/`` file for the role or
skill they are handed, live or retired, so a squad with leftovers from an older layout empties
out over its next ``sq sync``. Only a leftover whose role or skill was removed outright
survives, since the roster sweep never visits it; ``candidate_orphans`` reports it on the next
``sq adopt``.
"""

from squads import _aio
from squads._backends._agents_md import _managed as managed
from squads._backends._base import AgentBackend, Artifact, BackendContext
from squads._interactions._role_guidance import developer_roles
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._roles._projection import OperatorView, RoleView
from squads._workflow import ROSTER_SKILL
from squads._workflow._models import WorkflowSpec

_AGENTS_MD = "AGENTS.md"
_STAGING_DIR = ".agents_md"
_ROLES_DIR = "roles"
_SKILLS_DIR = "skills"


def _also_creatable_types(spec: WorkflowSpec, anchor_type: str | None) -> str:
    """The ``# also: ...`` list on the ``sq create <anchor>`` example line.

    Every other non-roster type the active spec declares, in its display order and never from a
    hardcoded list, so a dropped type does not appear and a renamed one appears under its new
    name. ``anchor_type`` is the generically derived type (:func:`cheatsheet_anchor_type`) the
    example line is built from, excluded so it is not listed against itself.
    """
    others = sorted(
        (t for t, ts in spec.items.items() if t != anchor_type and ts.category != "roster"),
        key=lambda t: (spec.items[t].order, t),
    )
    return "|".join(others)


class AgentsMdBackend(AgentBackend):
    """Answers to the five per-host questions of ``AgentBackend``.

    1. Command execution is not knowably available: ``AGENTS.md`` targets tools whose capability
       is declared by whoever builds a backend for them. So this backend keeps compiled roster
       prose (full name, slug, title, mission, responsibilities) instead of a fetch command.
    2. The expressible set is identity plus prose only: no ``model``, ``color``, capability
       boundary or preload list, and no place for a skill's ``operator_invocable``, since the
       document has no per-entry frontmatter.
    3. Not applicable: there is no per-entry file for a host to discover.
    4. No capability boundary is expressed, so the inherited :meth:`restriction_fragment`
       default (``None``) is correct.
    5. No per-entry artifact to render (the inherited :meth:`render_role_entry`/
       :meth:`render_skill_entry` default); ``write_managed`` compiles the whole document.
    """

    name = "agents_md"

    # ------------------------------------------------------------------ scaffold

    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        """Report AGENTS.md when it exists; it is created by :meth:`write_managed`, so a missing
        file is never mistaken for hand-written content."""
        agents_md = ctx.root / _AGENTS_MD
        if not await _aio.path_exists(agents_md):
            return []
        return [Artifact(ctx.rel(agents_md), "config", self.name)]

    # ------------------------------------------------------------------ managed files

    async def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]:
        """Compile roster, workflow cheatsheet, and role missions/responsibilities into AGENTS.md.

        Every role field comes from the ``RoleView`` the service passes in, never from text this
        backend rendered earlier: a declaration reaches this method as a view field or not at all
        (see ``RoleView`` for why that direction is a rule).
        """
        squad_dir = ctx.paths.config.squad_dir
        roles_data = [
            {
                "full_name": r.full_name,
                "title": r.title,
                "slug": r.slug,
                "pronouns": r.pronouns,
                "capabilities": list(r.capabilities),
                "mission": r.mission,
                "responsibilities": list(r.responsibilities),
            }
            for r in roster
        ]
        from squads._interactions._cheatsheet import (
            cheatsheet_anchor_context,
        )

        spec = ctx.spec
        anchor_ctx = cheatsheet_anchor_context(spec)
        section = render(
            "agents_md/agents_section.md.j2",
            from_squad=ctx.squad_dir,
            squad_dir=squad_dir,
            working_language=ctx.working_language,
            roles=roles_data,
            developer_slugs=[r.slug for r in developer_roles(roster, ctx.catalog())],
            operators=[
                {"full_name": o.full_name, "slug": o.slug, "pronouns": o.pronouns}
                for o in operators
            ],
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
        """Write nothing; return the pathless ``Artifact`` this ABC method must return.

        ``write_managed`` builds AGENTS.md from the ``RoleView`` roster alone, so there is no
        per-entry file to produce. It still deletes a leftover ``.agents_md/roles/<slug>.md``, so a
        live role's leftover goes by the next ``sq sync`` as a retired one's does via
        :meth:`remove_artifacts`. ``item`` and ``ctx.resolved_skills_for`` are unused: the compiled
        section carries no skills.
        """
        legacy = ctx.root / _STAGING_DIR / _ROLES_DIR / f"{role.slug}.md"
        await _aio.path_unlink(legacy, missing_ok=True)
        return Artifact(ctx.rel(legacy), "role_entry", self.name)

    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        """The skill-entry sibling of :meth:`generate_role_entry` — see its docstring."""
        slug = item.slug
        legacy = ctx.root / _STAGING_DIR / _SKILLS_DIR / f"{slug}.md"
        await _aio.path_unlink(legacy, missing_ok=True)
        return Artifact(ctx.rel(legacy), "skill_entry", self.name)

    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        """Delete any leftover per-item ``.agents_md/`` file for this entry (missing_ok
        semantics); this backend writes none of its own, see the module docstring. This is the
        withdrawal half of the same cleanup
        :meth:`generate_role_entry`/:meth:`generate_skill_entry` perform on materialisation, so
        a retired entry's leftover file disappears exactly as fast as a live one's.
        """
        slug = item.slug
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
        """Leftover ``.agents_md/roles/*.md``/``skills/*.md`` files naming no role/skill item.

        A file naming an item still in the roster, live or retired, never reaches here: the regular
        materialise/withdraw cycle of every ``sq sync`` deletes it first (see
        :meth:`generate_role_entry`, :meth:`generate_skill_entry`, :meth:`remove_artifacts`). Only
        the orphan of a fully removed item survives long enough to be reported. See the ABC
        docstring.
        """
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

    # managed_entry_paths is not overridden: this backend declares no per-entry pointers, which
    # is the ABC default (an empty list), so neither `sq check` nor `sq sync` names one.
