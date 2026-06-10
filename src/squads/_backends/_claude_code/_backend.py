"""Claude Code backend: writes thin pointer files into ``.claude/`` plus managed skill & CLAUDE.md.

The real definitions live under the squad folder; these files only route the agent there.
"""

import json
import shutil
from pathlib import Path
from typing import Any

from squads import _interactions as interactions
from squads._backends._base import AgentBackend, Artifact, BackendContext, OperatorView, RoleView
from squads._backends._claude_code import _claude_md as claude_md
from squads._backends._claude_code._frontmatter import normalize_model, oneline
from squads._models._enums import ItemType
from squads._models._extras import ExtraKey as X
from squads._models._item import Item
from squads._rendering._engine import render
from squads._roles._catalog import RoleDef

_AGENTS = "agents"
_SKILLS = "skills"
_SKILL_FILE = "SKILL.md"


class ClaudeCodeBackend(AgentBackend):
    name = "claude_code"

    # ------------------------------------------------------------------ scaffold
    def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        cdir = ctx.paths.claude_dir
        (cdir / _AGENTS).mkdir(parents=True, exist_ok=True)
        (cdir / _SKILLS / "squads").mkdir(parents=True, exist_ok=True)
        settings = cdir / "settings.json"
        self._merge_settings(settings)
        return [Artifact(ctx.rel(settings), "settings", self.name)]

    def _merge_settings(self, settings: Path) -> None:
        default: dict[str, Any] = json.loads(render("claude/settings.json.j2"))
        if settings.exists():
            current: dict[str, Any]
            try:
                current = json.loads(settings.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = {}
            perms: dict[str, Any] = current.setdefault("permissions", {})
            allow: list[str] = perms.setdefault("allow", [])
            for rule in default["permissions"]["allow"]:
                if rule not in allow:
                    allow.append(rule)
            perms.setdefault("deny", [])
            settings.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
        else:
            settings.write_text(json.dumps(default, indent=2) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------ managed files
    def write_managed(
        self, ctx: BackendContext, roster: list[RoleView], operators: list[OperatorView]
    ) -> list[Artifact]:
        squad_dir = ctx.paths.config.squad_dir
        artifacts: list[Artifact] = []
        # squads skill (real body under squads/agents/skills/, thin pointer in .claude/)
        artifacts += self._write_managed_skill(
            ctx,
            name="squads",
            description=(
                "How to track work on this project with the squads (`sq`) CLI: create/transition "
                "items, comment, link context. Use whenever you start, hand off, or update work."
            ),
            body=render("agents/squads_skill.md.j2", version=ctx.version, squad_dir=squad_dir),
        )
        # greeting skill — the start-of-conversation ritual (detect the human, register, greet)
        artifacts += self._write_managed_skill(
            ctx,
            name="greeting",
            description=(
                "Start of a conversation with a human: detect & register the operator, then greet "
                "them — match their tone, say how you help, and give a quick read of the project. "
                "Use when a person opens a session; skip it when spawned as a subagent for a job."
            ),
            body=render("agents/greeting_skill.md.j2", version=ctx.version, squad_dir=squad_dir),
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
        )
        claude_md.inject(ctx.paths.claude_md, section)
        artifacts.append(Artifact(ctx.rel(ctx.paths.claude_md), "claude_md", self.name))
        artifacts.extend(self._write_item_skills(ctx, roster))
        return artifacts

    def _write_managed_skill(
        self, ctx: BackendContext, *, name: str, description: str, body: str
    ) -> list[Artifact]:
        """Write a managed skill's real body under squads/ and a thin pointer in .claude/."""
        body_path = ctx.squad_dir / _AGENTS / _SKILLS / f"{name}.md"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(body, encoding="utf-8")
        pointer = ctx.paths.claude_dir / _SKILLS / name / _SKILL_FILE
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(
            render(
                "claude/pointer_skill.md.j2",
                slug=name,
                description=oneline(description),
                squad_path=ctx.rel(body_path),
            ),
            encoding="utf-8",
        )
        return [
            Artifact(ctx.rel(body_path), "skill_body", self.name),
            Artifact(ctx.rel(pointer), "skill_pointer", self.name),
        ]

    def _write_item_skills(self, ctx: BackendContext, roster: list[RoleView]) -> list[Artifact]:
        """One managed skill per item type, with a section per *active* interacting role.

        The shared ``developers`` section renders only when the roster has at least one developer
        (a ``<tech>-dev`` role), so a squad with no devs yet doesn't carry guidance for an actor
        that can't act.
        """
        by_slug = {r.slug: r for r in roster}
        has_dev = any(interactions.is_dev_slug(r.slug) for r in roster)
        out: list[Artifact] = []
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
            name = interactions.item_skill_name(item_type)
            body = render(
                "agents/item_skill.md.j2",
                title=item_type.value.capitalize(),
                type=item_type.value,
                version=ctx.version,
                overview=pb.overview,
                lifecycle=pb.lifecycle,
                commands=list(pb.commands),
                sections=sections,
            )
            out += self._write_managed_skill(
                ctx,
                name=name,
                description=(
                    f"Working with {item_type.value} items in this squad: "
                    "lifecycle, commands, and role-specific guidance."
                ),
                body=body,
            )
        return out

    # ------------------------------------------------------------------ pointers
    def generate_role_pointer(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        pointer = ctx.paths.claude_dir / _AGENTS / f"{role.slug}.md"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(
            render(
                "claude/pointer_agent.md.j2",
                slug=role.slug,
                full_name=role.full_name,
                role_title=role.title,
                description=oneline(role.description),
                model=normalize_model(role.model),
                color=role.color,
                squad_path=ctx.root_relative(item),
                skills=interactions.skills_for_role(role.slug),
            ),
            encoding="utf-8",
        )
        return Artifact(ctx.rel(pointer), "agent", self.name)

    def generate_skill_pointer(self, ctx: BackendContext, item: Item) -> Artifact:
        slug = item.extra.get(X.SLUG, item.slug)
        pointer = ctx.paths.claude_dir / _SKILLS / slug / _SKILL_FILE
        pointer.parent.mkdir(parents=True, exist_ok=True)
        description = item.extra.get(X.DESCRIPTION) or item.description or item.title
        pointer.write_text(
            render(
                "claude/pointer_skill.md.j2",
                slug=slug,
                description=oneline(description),
                squad_path=ctx.root_relative(item),
            ),
            encoding="utf-8",
        )
        return Artifact(ctx.rel(pointer), "skill_pointer", self.name)

    def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        slug = item.extra.get(X.SLUG, item.slug)
        if item.type is ItemType.SKILL:
            skill_dir = ctx.paths.claude_dir / _SKILLS / slug
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)
        else:
            (ctx.paths.claude_dir / _AGENTS / f"{slug}.md").unlink(missing_ok=True)
