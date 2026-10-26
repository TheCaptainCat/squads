"""Claude Code backend: writes thin pointer files into ``.claude/`` plus managed skill & CLAUDE.md.

The real definitions live under the squad folder; these files only route the agent there.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from squads import _aio
from squads import _sections as sections
from squads._backends._base import AgentBackend, Artifact, BackendContext
from squads._backends._claude_code import _claude_md as claude_md
from squads._backends._claude_code._frontmatter import (
    model_drop_warning,
    normalize_model,
    oneline,
)
from squads._interactions._playbook import managed_item_types
from squads._interactions._role_guidance import delegate_example_slugs, developer_roles
from squads._interactions._skills import (
    custom_item_skill_description,
    custom_item_skill_name,
    is_system_skill,
    item_skill_name,
    skill_description,
)
from squads._models import _markers as markers
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._roles._projection import OperatorView, RoleView
from squads._view_tags import place_view_tags
from squads._views import ITEM_SKILL_VIEW_NAME, SYSTEM_SKILL_VIEW_NAMES
from squads._workflow import ROSTER_SKILL

_AGENTS = "agents"
_SKILLS = "skills"
_SKILL_FILE = "SKILL.md"
_CLAUDE_DIR = ".claude"
_CLAUDE_MD = "CLAUDE.md"

#: The slug-bound startup commands an agent pointer names, in priority order: the concrete form
#: of the "Start of a run" protocol in ``claude/claude_section.md.j2``. One declaration, so a
#: command added here reaches every pointer; ``{slug}`` is filled per role by ``_startup_commands``.
_STARTUP_COMMAND_TEMPLATES: list[str] = [
    "sq memory {slug} list",
    "sq memory {slug} show <slug>",
    "sq board list",
    "sq mine {slug}",
    "sq inbox {slug}",
]


def _startup_commands(slug: str) -> list[str]:
    """The startup command set with *slug* substituted, in declared order."""
    return [c.format(slug=slug) for c in _STARTUP_COMMAND_TEMPLATES]


class ClaudeCodeBackend(AgentBackend):
    """Answers to the five per-host questions of ``AgentBackend``.

    1. Command execution: yes. A Claude Code agent runs `sq` itself, the containment rule's
       premise, so a runtime fetch substitutes for anything that only supplies content.
    2. The expressible set is this backend's whole frontmatter: ``name``, ``description``,
       ``model`` (``_VALID_MODELS``/``model_drop_warning``), ``color``, ``disallowedTools`` and
       the resolved ``skills`` list.
    3. The irreducible set is ``name`` and ``description``: Claude Code's discovery contract (a
       ``name``-keyed dispatch identifier plus selection text read before any agent runs).
    4. :meth:`restriction_fragment`: ``disallowedTools``, its spelling of the squad's spawn-tool
       attenuation.
    5. :meth:`render_role_entry`/:meth:`render_skill_entry`.
    """

    name = "claude_code"

    # ------------------------------------------------------------------ scaffold
    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        cdir = ctx.root / _CLAUDE_DIR
        await _aio.mkdir(cdir / _AGENTS, parents=True, exist_ok=True)
        await _aio.mkdir(cdir / _SKILLS / "squads", parents=True, exist_ok=True)
        settings = cdir / "settings.json"
        await self._merge_settings(ctx, settings)
        return [Artifact(ctx.rel(settings), "settings", self.name)]

    async def _merge_settings(self, ctx: BackendContext, settings: Path) -> None:
        default: dict[str, Any] = json.loads(
            render("claude/settings.json.j2", from_squad=ctx.squad_dir)
        )
        if await _aio.path_exists(settings):
            current: dict[str, Any]
            try:
                raw = await _aio.read_text(settings)
                current = json.loads(raw)
            except json.JSONDecodeError:
                current = {}
            perms: dict[str, Any] = current.setdefault("permissions", {})
            allow: list[str] = perms.setdefault("allow", [])
            for rule in default["permissions"]["allow"]:
                if rule not in allow:
                    allow.append(rule)
            perms.setdefault("deny", [])
            await _aio.write_text(settings, json.dumps(current, indent=2) + "\n")
        else:
            await _aio.write_text(settings, json.dumps(default, indent=2) + "\n")

    # ------------------------------------------------------------------ managed files
    async def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]:
        squad_dir = ctx.paths.config.squad_dir
        artifacts: list[Artifact] = []
        # The three always-on cross-role skills: a thin pointer in .claude/, and a body file
        # under squads/ whose sq:body region this writer seeds with that skill's own placement
        # tag (SYSTEM_SKILL_VIEW_NAMES) — see _write_managed_skill.
        spec = ctx.spec
        for slug, view_name in SYSTEM_SKILL_VIEW_NAMES.items():
            artifacts += await self._write_managed_skill(
                ctx,
                name=slug,
                description=skill_description(slug),
                body_tag=view_name if view_name in spec.views else None,
                invocable=ctx.operator_invocable(slug),
            )
        # CLAUDE.md managed section
        default = next((r for r in roster if r.is_default), None)
        section = render(
            "claude/claude_section.md.j2",
            from_squad=ctx.squad_dir,
            squad_dir=squad_dir,
            working_language=ctx.working_language,
            roles=[
                {
                    "full_name": r.full_name,
                    "title": r.title,
                    "slug": r.slug,
                    "pronouns": r.pronouns,
                    "capabilities": list(r.capabilities),
                }
                for r in roster
            ],
            delegate_examples=delegate_example_slugs(
                roster,
                default.slug if default else None,
                [r.slug for r in developer_roles(roster, ctx.catalog())],
            ),
            operators=[
                {"full_name": o.full_name, "slug": o.slug, "pronouns": o.pronouns}
                for o in operators
            ],
            # No live default role is legitimate: the template omits the default-role line and
            # the orchestration paragraph's name rather than inventing one, as the generated
            # skills' `has_dev` gate does when the last developer role retires.
            default_role_full_name=default.full_name if default else None,
            default_role_slug=default.slug if default else None,
            spec=spec,
            playbook=ctx.playbook,
        )
        claude_md_path = ctx.root / _CLAUDE_MD
        contradiction = await claude_md.inject(claude_md_path, section)
        warning = (
            f"{ctx.rel(claude_md_path)} had pre-existing hand-written content with no squads "
            "markers; the managed section was inserted at the top — review it for possible "
            "contradiction with that content."
            if contradiction
            else None
        )
        artifacts.append(Artifact(ctx.rel(claude_md_path), "claude_md", self.name, warning=warning))
        artifacts.extend(await self._write_item_skills(ctx))
        return artifacts

    async def _write_managed_skill(
        self,
        ctx: BackendContext,
        *,
        name: str,
        description: str,
        invocable: bool,
        body_tag: str | None = None,
    ) -> list[Artifact]:
        """Write a managed skill's thin .claude/ pointer and ensure its body file has a ``sq:body``.

        The region is empty when *body_tag* is ``None`` and seeded with the ``sq:view:<body_tag>``
        placement tag otherwise. This backend does not write a skill's definition: it renders on
        read off that tag (``squads._view_tags.expand_view_tags``, via ``ItemsMixin.read_body``).
        Every caller resolves *body_tag* against ``spec.views`` first and passes ``None`` for an
        undeclared view, so a tag naming one is never minted. The pointer needs neither shape;
        ``claude/pointer_skill.md.j2`` renders from *name*, *description* and *invocable* alone.

        What is owed is the file's shape: ``Service.seed_bundled_skills``/``seed_custom_skills``
        stamp a ``SKILL`` id onto the slug-named file written here, so a managed skill with no file
        is never seeded or indexed.

        Body path: if the skill is already indexed, it is resolved from ``item.path``
        (``agents/skills/SKILL-<NNNNNN>-<slug>.md``), the normal sync path. On a first write (``sq
        init``, before seeding) the slug-named ``agents/skills/<slug>.md`` is a temporary landing
        spot that ``seed_bundled_skills`` renames right after.

        A file that already carries a ``sq:body`` region is left byte-untouched whatever it holds,
        including a definition stored there earlier, which is a corpus concern healed by ``sq
        repair``'s backfill sweep (``MaintenanceMixin._repair_body_tag``). A second run over a
        synced squad therefore writes no skill body file and produces no diff.
        """
        # The body path comes from ctx.skill_paths (filled by refresh_managed(), since _backends
        # must not import _index). On a first write (`sq init`, before seeding) it is empty, so
        # fall back to a slug-named path under the declared skill folder, which an override may
        # have relocated; seed_bundled_skills renames it and rewrites the pointer.
        spec = ctx.spec
        resolved = ctx.skill_paths.get(name)
        if resolved is not None:
            body_path: Path = resolved
        else:
            body_path = ctx.squad_dir / spec.items[ROSTER_SKILL].folder / f"{name}.md"
        await _aio.mkdir(body_path.parent, parents=True, exist_ok=True)

        # A marker region, detectable on later syncs whether or not frontmatter is stamped yet.
        # body_tag is None for an undeclared view (the state _repair_body_tag leaves for a dropped
        # one), giving an empty untagged region. The tag goes through `place_view_tags` over an
        # empty region with no prose edit, so seeding is not a second spelling of placement.
        placed = place_view_tags(
            "",
            None,
            seeded=frozenset({body_tag}) if body_tag else frozenset(),
            spec=spec,
            item_type=ROSTER_SKILL,
            addr=name,
        )
        seed_body = sections.with_discussion_region(
            sections.replace_section(
                f"{markers.open_marker(markers.BODY)}{markers.close_marker(markers.BODY)}\n",
                markers.BODY,
                placed,
            )
        )

        if await _aio.path_exists(body_path):
            existing = await _aio.read_text(body_path)
            fm, _ = sections.split_frontmatter(existing, source=str(body_path))
            if not sections.has_section(existing, markers.BODY):
                # Region absent or partial: re-emit any frontmatter so a stamped id is never lost
                # and restore the region. Squad data (a possibly-indexed SKILL .md), hence atomic
                # replace; no frontmatter is invented, since allocation is a separate step.
                text = sections.join_frontmatter(fm, seed_body) if fm else seed_body
                on_disk = await _aio.read_text(body_path, verbatim=True)
                await _aio.atomic_write_text(
                    body_path, sections.conform_line_endings(on_disk, text)
                )
        else:
            await _aio.atomic_write_text(body_path, seed_body)

        pointer = ctx.root / _CLAUDE_DIR / _SKILLS / name / _SKILL_FILE
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        await _aio.write_text(
            pointer,
            self._render_skill_pointer(ctx, name, description, invocable=invocable),
        )
        return [Artifact(ctx.rel(pointer), "skill_pointer", self.name)]

    async def _write_item_skills(self, ctx: BackendContext) -> list[Artifact]:
        """One managed skill per item type: its ``.claude`` pointer and its body file's shape.

        The definition renders on read off the ``sq:view:item_skill`` tag seeded into every
        per-type skill's ``sq:body`` (``expand_view_tags``, via ``ItemsMixin.read_body``), like the
        permanently-system skills above. What remains here is which per-type skills a squad
        materialises, which needs no roster: the pointer renders from a slug and a description, and
        the tag names a view and nothing else. A type with no active-playbook entry, built-in or
        project-declared, still gets a skill, so the two loops below differ only in which vocabulary
        names the slug and description.
        """
        spec = ctx.spec
        playbook = ctx.playbook
        out: list[Artifact] = []
        # Gated like write_managed's body_tag and `_repair_body_tag`'s per-type branch: a dropped
        # `item_skill` view must never seed a dangling tag on a new skill body.
        item_skill_body_tag = ITEM_SKILL_VIEW_NAME if ITEM_SKILL_VIEW_NAME in spec.views else None

        # Types with a playbook entry, from the active playbook (ctx.playbook), not the bundled
        # one. A type the active spec dropped or renamed is skipped outright, so no skill
        # survives under the old name.
        for item_type in managed_item_types(playbook):
            if item_type not in spec.items:
                continue
            name = item_skill_name(item_type)
            out += await self._write_managed_skill(
                ctx,
                name=name,
                description=skill_description(name),
                body_tag=item_skill_body_tag,
                invocable=ctx.operator_invocable(name),
            )

        # Types with no active-playbook entry. This is the sole "custom vs built-in" line:
        # any type absent from the active playbook falls back here, bundled or not.
        for ctype, ctype_spec in ctx.spec.items.items():
            if ctype in playbook.types or ctype_spec.category == "roster":
                continue
            custom_name = custom_item_skill_name(ctype)
            out += await self._write_managed_skill(
                ctx,
                name=custom_name,
                description=custom_item_skill_description(ctype),
                body_tag=item_skill_body_tag,
                invocable=ctx.operator_invocable(custom_name),
            )
        return out

    # ------------------------------------------------------------------ entries
    @staticmethod
    def _resolve_model(role: RoleDef) -> tuple[str | None, str | None]:
        """Pair ``normalize_model`` with ``model_drop_warning`` in one place — every render
        path (write or pure) resolves a role's model through here, never through the
        normalizer alone, so a model this host cannot express is never dropped without also
        computing what would report it (whether or not this particular caller has anywhere to
        surface that warning)."""
        return normalize_model(role.model), model_drop_warning(role.slug, role.model)

    def _render_role_pointer(self, ctx: BackendContext, role: RoleDef, *, model: str | None) -> str:
        """The one place ``pointer_agent.md.j2`` is rendered — shared by
        :meth:`generate_role_entry` (writes it) and :meth:`render_role_entry` (question 5: the
        same render, without writing), so the two can never drift onto different content for
        the same role. *model* is already resolved (:meth:`_resolve_model`) — never normalized
        again here."""
        return render(
            "claude/pointer_agent.md.j2",
            from_squad=ctx.squad_dir,
            slug=role.slug,
            full_name=role.full_name,
            pronouns=role.pronouns,
            role_title=role.title,
            description=oneline(role.description),
            model=model,
            color=role.color,
            startup_commands=_startup_commands(role.slug),
            skills=ctx.resolved_skills_for(role),
            can_spawn=role.can_spawn,
        )

    async def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        pointer = ctx.root / _CLAUDE_DIR / _AGENTS / f"{role.slug}.md"
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        model, warning = self._resolve_model(role)
        await _aio.write_text(pointer, self._render_role_pointer(ctx, role, model=model))
        # WARN-only, never a refusal: a model this host cannot express is dropped from the
        # rendered pointer, and the artifact is what carries that fact back to the caller.
        return Artifact(ctx.rel(pointer), "agent", self.name, warning=warning)

    def _skill_pointer_description(self, ctx: BackendContext, item: Item, slug: str) -> str:
        """The description :meth:`generate_skill_entry` renders for *slug*.

        For a system skill (bundled or per-type ``sq-<type>``, :func:`interactions.is_system_skill`)
        the compiled-description call of :meth:`_write_managed_skill`/:meth:`_write_item_skills`
        runs last in a full ``sync``, so it is the slug's real current content, not *item*'s
        possibly seed-time-stale description. :meth:`render_skill_entry` (question 5) must answer
        with whichever writer ran last, or a system skill whose bundled text moved since seeding
        would read as permanently drifted. An author-defined skill has one writer
        (:meth:`generate_skill_entry`), so its own description is right.
        """
        spec = ctx.spec
        if is_system_skill(slug, spec):
            return skill_description(slug)
        return item.description or item.title

    def _render_skill_pointer(
        self, ctx: BackendContext, slug: str, description: str, *, invocable: bool
    ) -> str:
        """The one place ``pointer_skill.md.j2`` is rendered — shared by
        :meth:`_write_managed_skill`, :meth:`generate_skill_entry` and :meth:`render_skill_entry`,
        so the three can never drift onto different content for the same skill. *invocable* is
        already resolved by the engine."""
        return render(
            "claude/pointer_skill.md.j2",
            from_squad=ctx.squad_dir,
            slug=slug,
            description=oneline(description),
            invocable=invocable,
        )

    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        slug = item.slug
        pointer = ctx.root / _CLAUDE_DIR / _SKILLS / slug / _SKILL_FILE
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        description = self._skill_pointer_description(ctx, item, slug)
        await _aio.write_text(
            pointer,
            self._render_skill_pointer(
                ctx, slug, description, invocable=ctx.operator_invocable(slug, item)
            ),
        )
        return Artifact(ctx.rel(pointer), "skill_pointer", self.name)

    def restriction_fragment(self, role: RoleDef) -> str | None:
        """Question 4: ``disallowedTools: Agent`` — the literal line ``pointer_agent.md.j2``
        renders exactly when ``not role.can_spawn`` (see the template's own ``{% if %}``), or
        ``None`` when this role currently carries spawn authority and no restriction applies."""
        return None if role.can_spawn else "disallowedTools: Agent"

    def render_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> str | None:
        """Question 5 for a role — see :meth:`_render_role_pointer`, the shared render this
        reuses verbatim. The warning half of :meth:`_resolve_model` is discarded here (not
        ``_``-bound into unreachable code — this method has no caller with anywhere to report
        it), never skipped: the pairing itself is what the drop-report guard requires, and a
        model this host cannot express is still absent from the render either way."""
        model, _warning = self._resolve_model(role)
        return self._render_role_pointer(ctx, role, model=model)

    def render_skill_entry(self, ctx: BackendContext, item: Item) -> str | None:
        """Question 5 for a skill — see :meth:`_render_skill_pointer`/
        :meth:`_skill_pointer_description`, the shared render and description resolution this
        reuses verbatim."""
        slug = item.slug
        return self._render_skill_pointer(
            ctx,
            slug,
            self._skill_pointer_description(ctx, item, slug),
            invocable=ctx.operator_invocable(slug, item),
        )

    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        slug = item.slug
        cdir = ctx.root / _CLAUDE_DIR
        if item.type == ROSTER_SKILL:
            skill_dir = cdir / _SKILLS / slug
            if skill_dir.is_dir():
                await _aio.to_thread(lambda: shutil.rmtree(skill_dir))
        else:
            await _aio.path_unlink(cdir / _AGENTS / f"{slug}.md", missing_ok=True)

    async def candidate_orphans(
        self, ctx: BackendContext, roster: list[RoleView], skill_slugs: set[str]
    ) -> list[str]:
        """Every ``.claude/agents/*.md`` and ``.claude/skills/<name>/`` on disk whose slug
        matches no active role/skill — see the ABC docstring for the exact semantics."""
        known_roles = {r.slug for r in roster}
        cdir = ctx.root / _CLAUDE_DIR
        orphans: list[str] = []

        agents_dir = cdir / _AGENTS
        if await _aio.path_exists(agents_dir):
            paths = await _aio.to_thread(lambda: sorted(agents_dir.glob("*.md")))
            orphans += [ctx.rel(p) for p in paths if p.stem not in known_roles]

        skills_dir = cdir / _SKILLS
        if await _aio.path_exists(skills_dir):
            entries = await _aio.to_thread(lambda: sorted(skills_dir.iterdir()))
            orphans += [
                ctx.rel(p / _SKILL_FILE)
                for p in entries
                if p.is_dir() and p.name not in skill_slugs
            ]
        return orphans

    def managed_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative paths owned by this backend (present-only check; read-only)."""
        cdir = ctx.root / _CLAUDE_DIR
        return [
            ctx.rel(ctx.root / _CLAUDE_MD),
            ctx.rel(cdir / "settings.json"),
        ]

    def managed_entry_paths(self, ctx: BackendContext) -> list[str]:
        """Root-relative per-entry pointer paths for the roster-scoped live set in *ctx* —
        see the ABC docstring for the level/liveness contract."""
        cdir = ctx.root / _CLAUDE_DIR
        paths = [ctx.rel(cdir / _AGENTS / f"{slug}.md") for slug in sorted(ctx.live_role_slugs)]
        paths += [
            ctx.rel(cdir / _SKILLS / slug / _SKILL_FILE) for slug in sorted(ctx.live_skill_slugs)
        ]
        return paths
