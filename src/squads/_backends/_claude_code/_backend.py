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
from squads._backends._claude_code._frontmatter import normalize_model, oneline
from squads._models import _markers as markers
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef
from squads._workflow import ROSTER_SKILL, linearize_lifecycle

_AGENTS = "agents"
_SKILLS = "skills"
_SKILL_FILE = "SKILL.md"
_CLAUDE_DIR = ".claude"
_CLAUDE_MD = "CLAUDE.md"


class ClaudeCodeBackend(AgentBackend):
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
        # squads skill (real body under squads/agents/skills/, thin pointer in .claude/)
        from squads._workflow import bundled_spec

        spec = ctx.spec if ctx.spec is not None else bundled_spec()
        artifacts += await self._write_managed_skill(
            ctx,
            name="squads",
            description=interactions.skill_description("squads"),
            body=render(
                "agents/squads_skill.md.j2",
                squad_dir=squad_dir,
                spec=spec,
            ),
        )
        # greeting skill — the start-of-conversation ritual (detect the human, register, greet)
        artifacts += await self._write_managed_skill(
            ctx,
            name="greeting",
            description=interactions.skill_description("greeting"),
            body=render("agents/greeting_skill.md.j2", squad_dir=squad_dir),
        )
        # sq-memory skill — cross-role memory workflow + curation discipline
        artifacts += await self._write_managed_skill(
            ctx,
            name=interactions.MEMORY_SKILL,
            description=interactions.skill_description(interactions.MEMORY_SKILL),
            body=render("agents/memory_skill.md.j2", squad_dir=squad_dir),
        )
        # CLAUDE.md managed section
        default = next((r for r in roster if r.is_default), None)
        section = render(
            "claude/claude_section.md.j2",
            squad_dir=squad_dir,
            roles=[{"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in roster],
            operators=[{"full_name": o.full_name, "slug": o.slug} for o in operators],
            default_role_full_name=default.full_name if default else "the manager",
            default_role_slug=default.slug if default else "manager",
            spec=spec,
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
        artifacts.extend(await self._write_item_skills(ctx, roster))
        return artifacts

    async def _write_managed_skill(
        self, ctx: BackendContext, *, name: str, description: str, body: str
    ) -> list[Artifact]:
        """Write a managed skill's real body under squads/ and a thin pointer in .claude/.

        Body path derivation:
        - If the skill is already in the index (i.e. it has been stamped as a SKILL item),
          the body path is resolved from ``item.path`` — which encodes the convention-correct
          name ``agents/skills/SKILL-<NNNNNN>-<slug>.md``.  This is the normal sync path.
        - On a first write (no index entry yet — during ``sq init`` before ``seed_bundled_skills``
          runs), the legacy slug-named path ``agents/skills/<slug>.md`` is used as a temporary
          landing spot.  ``seed_bundled_skills`` will rename it to the convention name
          immediately afterwards.

        Body-region-only regen: if the skill file already exists and carries sq frontmatter
        (i.e. it has been stamped as a SKILL item), only the ``sq:body`` region is replaced —
        the frontmatter and every other region are left intact.

        If the file does not yet exist or has no frontmatter, the body is written wrapped in
        ``sq:body`` markers so the file is region-compatible for future frontmatter-preserving
        regenerations (invariant 3).
        """
        # Resolve the body path from the caller-supplied skill_paths map.
        # refresh_managed() populates ctx.skill_paths from the index before calling
        # write_managed, so this backend never needs to load the index itself
        # (layering invariant: _backends must not import _index).
        #
        # On first write (sq init, before seeding): skill_paths is empty so we fall back
        # to a slug-named temporary path; seed_bundled_skills renames it to the convention
        # name right after and rewrites the pointer.
        resolved = ctx.skill_paths.get(name)
        body_path: Path = (
            resolved if resolved is not None else (ctx.squad_dir / _AGENTS / _SKILLS / f"{name}.md")
        )
        await _aio.mkdir(body_path.parent, parents=True, exist_ok=True)

        # Wrap the rendered body in sq:body markers so the file is marker-structured.
        # This makes the region detectable on subsequent syncs regardless of whether
        # frontmatter has been stamped yet.
        body_with_markers = (
            f"{markers.open_marker(markers.BODY)}\n{body}\n{markers.close_marker(markers.BODY)}\n"
        )

        if await _aio.path_exists(body_path):
            existing = await _aio.read_text(body_path)
            fm, _ = sections.split_frontmatter(existing)
            if fm and sections.has_section(existing, markers.BODY):
                # File has been stamped with frontmatter: preserve it, only update body region.
                new_inner = f"\n{body}\n"
                updated = sections.replace_section(existing, markers.BODY, new_inner)
                await _aio.write_text(body_path, updated)
            elif fm:
                # Frontmatter present but sq:body region absent/partial — fail-safe: re-emit
                # the existing frontmatter so the stamped id/sequence_id are never lost.
                # Body region becomes freshly wrapped.
                await _aio.write_text(body_path, sections.join_frontmatter(fm, body_with_markers))
            else:
                # Genuinely no frontmatter (first-write or pre-stamp file): write bare body
                # with markers.  We do NOT invent frontmatter here — allocation is a separate
                # step.
                await _aio.write_text(body_path, body_with_markers)
        else:
            await _aio.write_text(body_path, body_with_markers)

        pointer = ctx.root / _CLAUDE_DIR / _SKILLS / name / _SKILL_FILE
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        await _aio.write_text(
            pointer,
            render(
                "claude/pointer_skill.md.j2",
                slug=name,
                description=oneline(description),
                squad_path=ctx.rel(body_path),
            ),
        )
        return [
            Artifact(ctx.rel(body_path), "skill_body", self.name),
            Artifact(ctx.rel(pointer), "skill_pointer", self.name),
        ]

    async def _write_item_skills(
        self, ctx: BackendContext, roster: list[RoleView]
    ) -> list[Artifact]:
        """One managed skill per item type, with a section per *active* interacting role.

        The shared ``developers`` section renders only when the roster has at least one developer
        (a ``<tech>-dev`` role), so a squad with no devs yet doesn't carry guidance for an actor
        that can't act.

        A type with no ``PLAYBOOK`` entry — built-in or project-declared alike (F4; there is no
        static built-in/custom split any more) — also gets a thin auto-generated skill: lifecycle
        string (from ``linearize_lifecycle``), the standard command list, and no role sections
        (graceful degradation).
        """
        from squads._workflow import bundled_spec

        by_slug = {r.slug: r for r in roster}
        has_dev = any(interactions.is_dev_slug(r.slug) for r in roster)
        spec = ctx.spec if ctx.spec is not None else bundled_spec()
        out: list[Artifact] = []

        # Types with a PLAYBOOK entry — rich skill with full role guidance.
        for item_type in interactions.managed_item_types():
            pb = interactions.PLAYBOOK[item_type]
            sections: list[dict[str, Any]] = []
            for guide in pb.roles:
                if guide.slug == interactions.DEV:
                    if not has_dev:
                        continue
                    title = "developers"
                elif guide.slug in by_slug:
                    r = by_slug[guide.slug]
                    title = f"{r.full_name} (`{r.slug}`)"
                else:
                    continue
                sections.append(
                    {
                        "title": title,
                        "enter": guide.enter,
                        "do": guide.do,
                        "handoff": guide.handoff,
                        "watch": guide.watch,
                    }
                )
            # Lifecycle + sub-entity kind derive from the active spec (not the frozen
            # playbook prose) so an override on a kept built-in type stays correct; fall
            # back to the frozen string only if the type itself was dropped from the spec.
            subentity_kind = spec.item_subentity_kind(item_type)
            lifecycle_str = (
                linearize_lifecycle(spec.machine_for(item_type))
                if item_type in spec.items
                else pb.lifecycle
            )
            name = interactions.item_skill_name(item_type)
            body = render(
                "agents/item_skill.md.j2",
                title=item_type.capitalize(),
                type=item_type,
                overview=pb.overview,
                lifecycle=lifecycle_str,
                commands=list(pb.commands),
                sections=sections,
                subentity_kind=subentity_kind,
                subentity_plural=spec.subentity_plural(subentity_kind) if subentity_kind else None,
            )
            out += await self._write_managed_skill(
                ctx,
                name=name,
                description=interactions.skill_description(name),
                body=body,
            )

        # Types with no PLAYBOOK entry — thin skill with auto-derived lifecycle + standard
        # command list. This is the sole "custom vs built-in" line now: any type absent
        # from PLAYBOOK falls back here, whether or not it happens to be a bundled type.
        if ctx.spec is not None:
            for ctype, ctype_spec in ctx.spec.items.items():
                if ctype in interactions.PLAYBOOK or ctype_spec.category == "roster":
                    continue
                machine = ctx.spec.machine_for(ctype)
                lifecycle_str = linearize_lifecycle(machine)
                name = interactions.custom_item_skill_name(ctype)
                body = render(
                    "agents/item_skill.md.j2",
                    title=ctype.capitalize(),
                    type=ctype,
                    overview="",
                    lifecycle=lifecycle_str,
                    commands=interactions.custom_item_skill_commands(ctype),
                    sections=[],
                    subentity_kind=None,
                    subentity_plural=None,
                )
                out += await self._write_managed_skill(
                    ctx,
                    name=name,
                    description=interactions.custom_item_skill_description(ctype),
                    body=body,
                )
        return out

    # ------------------------------------------------------------------ entries
    async def generate_role_entry(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        pointer = ctx.root / _CLAUDE_DIR / _AGENTS / f"{role.slug}.md"
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        await _aio.write_text(
            pointer,
            render(
                "claude/pointer_agent.md.j2",
                slug=role.slug,
                full_name=role.full_name,
                role_title=role.title,
                description=oneline(role.description),
                model=normalize_model(role.model),
                color=role.color,
                squad_path=ctx.root_relative(item),
                skills=ctx.resolved_skills_for(role.slug),
                can_spawn=role.can_spawn,
            ),
        )
        return Artifact(ctx.rel(pointer), "agent", self.name)

    async def generate_skill_entry(self, ctx: BackendContext, item: Item) -> Artifact:
        slug = item.extra.get(X.SLUG, item.slug)
        pointer = ctx.root / _CLAUDE_DIR / _SKILLS / slug / _SKILL_FILE
        await _aio.mkdir(pointer.parent, parents=True, exist_ok=True)
        description = item.extra.get(X.DESCRIPTION) or item.description or item.title
        await _aio.write_text(
            pointer,
            render(
                "claude/pointer_skill.md.j2",
                slug=slug,
                description=oneline(description),
                squad_path=ctx.root_relative(item),
            ),
        )
        return Artifact(ctx.rel(pointer), "skill_pointer", self.name)

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
