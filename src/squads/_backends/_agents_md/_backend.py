"""agents_md backend: writes/refreshes a single AGENTS.md at the project root.

``write_managed`` compiles the whole file — roster, workflow cheatsheet, per-role
mission/responsibilities — entirely from the ``RoleView``s/``OperatorView``s it is passed.
``generate_role_entry``/``generate_skill_entry`` write nothing: they exist only to satisfy the
``AgentBackend`` ABC's per-entry method contract, which this backend has no per-entry file to
back. A prior version of this backend staged one file per role/skill under
``.agents_md/roles/``/``.agents_md/skills/`` purely so those two methods had something to name
as an ``Artifact`` — nothing ever read them back: not ``write_managed`` (which builds AGENTS.md
from the roster view alone) and not any external agent tool, which reads ``AGENTS.md`` itself.

Those staging files are gone. This backend no longer creates them, and materialising or
withdrawing a roster entry now opportunistically deletes any leftover one a pre-upgrade version
left behind, so an existing squad's stale ``.agents_md/`` directory empties out over the very
next ``sq sync`` — for every role/skill still known to the roster, live or retired alike (see
``generate_role_entry``/``generate_skill_entry``/``remove_artifacts`` below). Only a leftover
file whose owning role/skill was removed outright survives a sync (nothing in the roster sweep
ever visits it) — ``candidate_orphans`` still reports that one, unchanged, the next time
``sq adopt`` runs.
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
    """Question 1: **not knowably** — this is the answer, not a gap. ``AGENTS.md`` targets
    tools whose command-execution capability is declared by whoever builds a backend for them,
    not by us; not knowing a host's capabilities is the normal condition for every backend an
    adopter brings, not a hole in our knowledge to work around. That is why this backend keeps
    compiled roster prose (full name, slug, title, mission, responsibilities) instead of a
    fetch command: clause 2 asks whether a runtime fetch can substitute, and a host that cannot
    run a command has no fetch available.
    Question 2: the expressible set is identity plus prose only — no ``model``, no ``color``, no
    capability-boundary field, no preload list: the compiled document has no per-entry frontmatter
    at all, only the roster/mission text ``write_managed`` renders.
    Question 3: not applicable — there is no per-entry file for a host to discover and dispatch;
    ``AGENTS.md`` is one whole document, found the way the host finds any file.
    Question 4: no capability boundary is expressed (:meth:`restriction_fragment`'s inherited
    ``None`` default is the honest answer, not an oversight) — the compiled document carries no
    field a host could read as a spawn restriction.
    Question 5: no per-entry artifact to render (:meth:`render_role_entry`/
    :meth:`render_skill_entry`'s inherited ``None`` default) — ``write_managed`` compiles the
    whole document from the roster view in one pass; see the module docstring for why
    ``generate_role_entry``/``generate_skill_entry`` write nothing to render a pure copy of.
    """

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

        Every role field rendered here comes from the ``RoleView``s the service passes in —
        never from ``generate_role_entry``/``generate_skill_entry``, which write nothing (see
        the module docstring).

        They used to be: ``RoleView`` carried no ``mission``, so this method recovered it by
        matching the literal ``**Mission:**`` prefix on a line of the markdown
        ``generate_role_entry`` had just rendered from a per-role staging file. That made a
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
        """Write nothing; return the pathless ``Artifact`` this ABC method must return.

        ``write_managed`` builds AGENTS.md from the ``RoleView`` roster alone (see the module
        docstring), so this backend has no per-entry file to produce. Still deletes any
        ``.agents_md/roles/<slug>.md`` a pre-upgrade version of this backend left behind — the
        materialise half of this release's staging-file removal, so a *live* role's leftover
        file is gone by the next ``sq sync`` exactly as a retired one's already is via
        :meth:`remove_artifacts`. ``item``/``ctx.resolved_skills_for`` are unused: nothing here
        renders a role's skills any more (the compiled section never has).
        """
        legacy = ctx.root / _STAGING_DIR / _ROLES_DIR / f"{role.slug}.md"
        await _aio.path_unlink(legacy, missing_ok=True)
        return Artifact(ctx.rel(legacy), "role_entry", self.name)

    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        """The skill-entry sibling of :meth:`generate_role_entry` — see its docstring."""
        slug = item.extra.get(X.SLUG, item.slug)
        legacy = ctx.root / _STAGING_DIR / _SKILLS_DIR / f"{slug}.md"
        await _aio.path_unlink(legacy, missing_ok=True)
        return Artifact(ctx.rel(legacy), "skill_entry", self.name)

    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        """Delete any leftover per-item staging file from a pre-upgrade version of this
        backend (missing_ok semantics) — this backend no longer writes one; see the module
        docstring. This is the withdrawal half of the same cleanup
        :meth:`generate_role_entry`/:meth:`generate_skill_entry` perform on materialisation, so
        a retired entry's leftover file disappears exactly as fast as a live one's.
        """
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
        """Leftover ``.agents_md/roles/*.md``/``.agents_md/skills/*.md`` staging files from a
        pre-upgrade version of this backend whose slug names no role/skill item at all.

        One naming an item still in the roster — live or retired — never reaches here: the
        ordinary materialise/withdraw cycle every ``sq sync`` already runs deletes it first
        (see :meth:`generate_role_entry`/:meth:`generate_skill_entry`/:meth:`remove_artifacts`).
        Only a fully-removed item's own orphaned file, which no sync pass ever visits, survives
        long enough to be reported here. See the ABC docstring for the general semantics.
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

    # managed_entry_paths: no override — this backend declares no per-entry pointers (see the
    # module docstring), which is exactly what the ABC default (an empty list) means. Neither
    # `sq check`'s backend_reconciled rule nor `sq sync`'s regeneration report name a staging
    # file for this backend any more.
