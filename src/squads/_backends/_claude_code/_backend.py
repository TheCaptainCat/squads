"""Claude Code backend: writes thin pointer files into ``.claude/`` plus managed skill & CLAUDE.md.

The real definitions live under the squad folder; these files only route the agent there.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from squads import _aio
from squads import _interactions as interactions
from squads import _sections as sections
from squads._backends._base import AgentBackend, Artifact, BackendContext, OperatorView, RoleView
from squads._backends._claude_code import _claude_md as claude_md
from squads._backends._claude_code._frontmatter import (
    model_drop_warning,
    normalize_model,
    oneline,
)
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._workflow import ROSTER_SKILL

_AGENTS = "agents"
_SKILLS = "skills"
_SKILL_FILE = "SKILL.md"
_CLAUDE_DIR = ".claude"
_CLAUDE_MD = "CLAUDE.md"

#: The slug-bound startup command set an agent pointer names, in priority order — the concrete
#: rendering of the protocol CLAUDE.md's managed section states generically for every agent
#: (``claude/claude_section.md.j2``'s "Start of a run" section). One declaration, so a command
#: added here appears on every generated agent pointer with no template edit.
#: ``{slug}`` is substituted per role by ``_startup_commands``.
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
    """Question 1: **yes** — a Claude Code agent runs `sq` itself, which is the containment
    rule's whole premise, so a runtime fetch substitutes for anything that only *supplies*
    content.
    Question 2: the expressible set is this backend's whole frontmatter surface — ``name``,
    ``description``, ``model`` (``_VALID_MODELS``/``model_drop_warning`` below), ``color``,
    ``disallowedTools``, the resolved ``skills`` list; nothing squads projects onto a role falls
    outside it today.
    Question 3: the irreducible set is ``name`` and ``description`` — Claude Code's own
    discovery contract (a `name`-keyed dispatch identifier plus the selection text read before
    any agent exists to run anything).
    Question 4: :meth:`restriction_fragment` — ``disallowedTools``, Claude Code's spelling of
    the squad's own spawn-tool attenuation.
    Question 5: :meth:`render_role_entry`/:meth:`render_skill_entry`.
    """

    name = "claude_code"

    # ------------------------------------------------------------------ scaffold
    async def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        cdir = ctx.root / _CLAUDE_DIR
        await _aio.mkdir(cdir / _AGENTS, parents=True, exist_ok=True)
        await _aio.mkdir(cdir / _SKILLS / "squads", parents=True, exist_ok=True)
        settings = cdir / "settings.json"
        await self._merge_settings(settings)
        return [Artifact(ctx.rel(settings), "settings", self.name)]

    async def _merge_settings(self, settings: Path) -> None:
        default: dict[str, Any] = json.loads(render("claude/settings.json.j2"))
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
        # under squads/ whose sq:body region this backend leaves for the service to render at
        # read time (ServiceCore.skill_definition_text) — see _write_managed_skill.
        from squads._workflow import bundled_spec

        spec = ctx.spec if ctx.spec is not None else bundled_spec()
        for slug in (
            interactions.SQUADS_SKILL,
            interactions.GREETING_SKILL,
            interactions.MEMORY_SKILL,
        ):
            artifacts += await self._write_managed_skill(
                ctx, name=slug, description=interactions.skill_description(slug)
            )
        # CLAUDE.md managed section
        default = next((r for r in roster if r.is_default), None)
        section = render(
            "claude/claude_section.md.j2",
            squad_dir=squad_dir,
            roles=[{"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in roster],
            operators=[{"full_name": o.full_name, "slug": o.slug} for o in operators],
            # No live role carrying `is_default` is a legitimate state, not a gap to paper over
            # with a fabricated slug: the template omits the default-role line and the
            # orchestration paragraph's name entirely rather than inventing one, the same
            # degradation the generated skills' `has_dev` gate performs when the last developer
            # role retires (that gate lives with the render, on ServiceCore).
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
        self, ctx: BackendContext, *, name: str, description: str
    ) -> list[Artifact]:
        """Write a managed skill's thin pointer in .claude/, and make sure its body file under
        squads/ exists with a well-formed, EMPTY ``sq:body`` region.

        **This backend does not write a system skill's definition.** That text renders on read,
        from the service (``ServiceCore.skill_definition_text``), so nothing here needs it and
        the pointer never did: ``claude/pointer_skill.md.j2`` renders from *name* and
        *description* alone.

        What is still owed is the file's *shape*. The seeding step
        (``Service.seed_bundled_skills``/``seed_custom_skills``) stamps a ``SKILL`` id onto the
        slug-named file this writes, so a managed skill with no file on disk is never seeded and
        never becomes an indexed item at all.

        Body path derivation:
        - If the skill is already in the index (i.e. it has been stamped as a SKILL item),
          the body path is resolved from ``item.path`` — which encodes the convention-correct
          name ``agents/skills/SKILL-<NNNNNN>-<slug>.md``.  This is the normal sync path.
        - On a first write (no index entry yet — during ``sq init`` before ``seed_bundled_skills``
          runs), the legacy slug-named path ``agents/skills/<slug>.md`` is used as a temporary
          landing spot.  ``seed_bundled_skills`` will rename it to the convention name
          immediately afterwards.

        A file that already carries a ``sq:body`` region is left byte-untouched, whatever that
        region holds — including a definition an older release stored there, which is a corpus
        concern and not this writer's to rewrite. So a second run over a synced squad writes no
        skill body file at all, and produces no diff on one.
        """
        # Resolve the body path from the caller-supplied skill_paths map.
        # refresh_managed() populates ctx.skill_paths from the index before calling
        # write_managed, so this backend never needs to load the index itself
        # (layering invariant: _backends must not import _index).
        #
        # On first write (sq init, before seeding): skill_paths is empty so we fall back
        # to a slug-named temporary path under the *declared* skill folder (an override
        # may have relocated it before init ever ran); seed_bundled_skills renames it to
        # the convention name right after and rewrites the pointer.
        from squads._workflow import bundled_spec

        resolved = ctx.skill_paths.get(name)
        if resolved is not None:
            body_path: Path = resolved
        else:
            spec = ctx.spec if ctx.spec is not None else bundled_spec()
            body_path = ctx.squad_dir / spec.items[ROSTER_SKILL].folder / f"{name}.md"
        await _aio.mkdir(body_path.parent, parents=True, exist_ok=True)

        # An empty, marker-structured region: detectable on subsequent syncs regardless of
        # whether frontmatter has been stamped yet, and the shape every item file shares.
        empty_body = f"{markers.open_marker(markers.BODY)}\n{markers.close_marker(markers.BODY)}\n"

        if await _aio.path_exists(body_path):
            existing = await _aio.read_text(body_path)
            fm, _ = sections.split_frontmatter(existing, source=str(body_path))
            if not sections.has_section(existing, markers.BODY):
                # Region absent or partial. Fail-safe: re-emit any frontmatter that is there so
                # a stamped id/sequence_id is never lost, and give the file the region back.
                # This is squad data (a possibly-indexed SKILL item's .md) — atomic replace,
                # not the plain truncating writer. No frontmatter is invented here when there
                # is none: allocation is a separate step.
                text = sections.join_frontmatter(fm, empty_body) if fm else empty_body
                await _aio.atomic_write_text(body_path, text)
        else:
            await _aio.atomic_write_text(body_path, empty_body)

        pointer = ctx.root / _CLAUDE_DIR / _SKILLS / name / _SKILL_FILE
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        await _aio.write_text(
            pointer,
            render(
                "claude/pointer_skill.md.j2",
                slug=name,
                description=oneline(description),
            ),
        )
        return [Artifact(ctx.rel(pointer), "skill_pointer", self.name)]

    async def _write_item_skills(self, ctx: BackendContext) -> list[Artifact]:
        """One managed skill per item type: its ``.claude`` pointer, and its body file's shape.

        The definitions themselves are not written here — they render on read, from the service
        (``ServiceCore.skill_definition_text``), which is also where the rich/thin split and the
        ``has_dev`` gate on the shared ``developers`` section now live. What survives in this
        backend is the enumeration: which per-type skills a squad materialises at all — which
        needs no roster, since a pointer is rendered from a slug and a description.

        A type with no entry in the active playbook — built-in or project-declared alike (there
        is no static built-in/custom split any more) — still gets its own skill, so the two
        loops below differ in nothing but which vocabulary names the slug and the description.
        """
        from squads._workflow import bundled_spec

        spec = ctx.spec if ctx.spec is not None else bundled_spec()
        playbook = ctx.playbook if ctx.playbook is not None else interactions.get_playbook_spec()
        out: list[Artifact] = []

        # Types with a playbook entry. The active, per-request playbook (ctx.playbook, merged
        # with any .overrides/playbook.toml) decides this set, not the bundled singleton. A type
        # the active spec has dropped or renamed away must produce no skill at all — never a
        # stale one under its old name — so a type absent from the active spec is skipped
        # outright: the "no orphan" bar a shadowing override has to clear.
        for item_type in interactions.managed_item_types(playbook):
            if item_type not in spec.items:
                continue
            name = interactions.item_skill_name(item_type)
            out += await self._write_managed_skill(
                ctx, name=name, description=interactions.skill_description(name)
            )

        # Types with no active-playbook entry. This is the sole "custom vs built-in" line now:
        # any type absent from the active playbook falls back here, bundled or not.
        if ctx.spec is not None:
            for ctype, ctype_spec in ctx.spec.items.items():
                if ctype in playbook.types or ctype_spec.category == "roster":
                    continue
                out += await self._write_managed_skill(
                    ctx,
                    name=interactions.custom_item_skill_name(ctype),
                    description=interactions.custom_item_skill_description(ctype),
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
            slug=role.slug,
            full_name=role.full_name,
            role_title=role.title,
            description=oneline(role.description),
            model=model,
            color=role.color,
            startup_commands=_startup_commands(role.slug),
            skills=ctx.resolved_skills_for(role.slug),
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
        """The description :meth:`generate_skill_entry` renders for *slug* — but for a
        **system** skill (bundled or a per-type ``sq-<type>``, :func:`interactions
        .is_system_skill`), ``write_managed``'s own compiled-description call
        (:meth:`_write_managed_skill`/:meth:`_write_item_skills`) is what runs *last* in a full
        ``sync`` and so is this slug's real current content, not *item*'s own (possibly
        seed-time-stale — nothing refreshes a ``SKILL`` item's ``description`` the way
        ``_refresh_catalog_extra`` refreshes a role's) description. :meth:`render_skill_entry`
        (question 5) must answer with whichever of the two is actually this slug's last writer,
        or a system skill whose bundled description text moved since it was seeded would read
        as permanently drifted. An author-defined (non-system) skill has only one writer
        (:meth:`generate_skill_entry` itself), so its own description is exactly right.
        """
        from squads._workflow import bundled_spec

        spec = ctx.spec if ctx.spec is not None else bundled_spec()
        if interactions.is_system_skill(slug, spec):
            return interactions.skill_description(slug)
        return item.extra.get(X.DESCRIPTION) or item.description or item.title

    def _render_skill_pointer(self, slug: str, description: str) -> str:
        """The one place ``pointer_skill.md.j2`` is rendered for an item-scoped skill entry —
        shared by :meth:`generate_skill_entry` and :meth:`render_skill_entry`, same rationale
        as :meth:`_render_role_pointer`. ``_write_managed_skill`` renders the same template
        directly for the compiled managed skills (squads/greeting/memory/per-type) — that path
        stays separate since it has no ``Item`` to hand this method, but both calls pass through
        the identical ``oneline``-normalised template with the same two variables."""
        return render("claude/pointer_skill.md.j2", slug=slug, description=oneline(description))

    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        slug = item.extra.get(X.SLUG, item.slug)
        pointer = ctx.root / _CLAUDE_DIR / _SKILLS / slug / _SKILL_FILE
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        description = item.extra.get(X.DESCRIPTION) or item.description or item.title
        await _aio.write_text(pointer, self._render_skill_pointer(slug, description))
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
        slug = item.extra.get(X.SLUG, item.slug)
        return self._render_skill_pointer(slug, self._skill_pointer_description(ctx, item, slug))

    async def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        slug = item.extra.get(X.SLUG, item.slug)
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
