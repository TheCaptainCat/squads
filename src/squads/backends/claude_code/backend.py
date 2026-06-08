"""Claude Code backend: writes thin pointer files into ``.claude/`` plus managed skill & CLAUDE.md.

The real definitions live under the squad folder; these files only route the agent there.
"""

import json
from pathlib import Path
from typing import Any

from squads.backends.base import AgentBackend, Artifact, BackendContext, RoleView
from squads.backends.claude_code import claude_md
from squads.backends.claude_code.frontmatter import normalize_model, oneline
from squads.models.item import Item
from squads.rendering import render
from squads.roles.catalog import RoleDef


class ClaudeCodeBackend(AgentBackend):
    name = "claude_code"

    # ------------------------------------------------------------------ scaffold
    def ensure_scaffold(self, ctx: BackendContext) -> list[Artifact]:
        cdir = ctx.paths.claude_dir
        (cdir / "agents").mkdir(parents=True, exist_ok=True)
        (cdir / "skills" / "squads").mkdir(parents=True, exist_ok=True)
        settings = cdir / "settings.json"
        self._merge_settings(settings)
        return [Artifact(self._rel(ctx, settings), "settings", self.name)]

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
    def write_managed(self, ctx: BackendContext, roster: list[RoleView]) -> list[Artifact]:
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
        # CLAUDE.md managed section
        default = next((r for r in roster if r.is_default), None)
        section = render(
            "claude/claude_section.md.j2",
            squad_dir=squad_dir,
            roles=[{"full_name": r.full_name, "title": r.title, "slug": r.slug} for r in roster],
            default_role_full_name=default.full_name if default else "the manager",
            default_role_slug=default.slug if default else "manager",
        )
        claude_md.inject(ctx.paths.claude_md, section)
        artifacts.append(Artifact(self._rel(ctx, ctx.paths.claude_md), "claude_md", self.name))
        artifacts.extend(self._write_item_skills(ctx, roster))
        return artifacts

    def _write_managed_skill(
        self, ctx: BackendContext, *, name: str, description: str, body: str
    ) -> list[Artifact]:
        """Write a managed skill's real body under squads/ and a thin pointer in .claude/."""
        body_path = ctx.squad_dir / "agents" / "skills" / f"{name}.md"
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(body, encoding="utf-8")
        pointer = ctx.paths.claude_dir / "skills" / name / "SKILL.md"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        pointer.write_text(
            render(
                "claude/pointer_skill.md.j2",
                slug=name,
                description=oneline(description),
                squad_path=self._rel(ctx, body_path),
            ),
            encoding="utf-8",
        )
        return [
            Artifact(self._rel(ctx, body_path), "skill_body", self.name),
            Artifact(self._rel(ctx, pointer), "skill_pointer", self.name),
        ]

    def _write_item_skills(self, ctx: BackendContext, roster: list[RoleView]) -> list[Artifact]:
        """One managed skill per item type, with a section per *active* interacting role."""
        from squads import interactions

        by_slug = {r.slug: r for r in roster}
        out: list[Artifact] = []
        for item_type in interactions.managed_item_types():
            pb = interactions.PLAYBOOK[item_type]
            sections: list[dict[str, str]] = []
            for guide in pb.roles:
                if guide.slug == interactions.DEV:
                    sections.append({"title": "developers", "text": guide.text})
                elif guide.slug in by_slug:
                    r = by_slug[guide.slug]
                    sections.append({"title": f"{r.full_name} (`{r.slug}`)", "text": guide.text})
            name = interactions.item_skill_name(item_type)
            body = render(
                "agents/item_skill.md.j2",
                title=item_type.value.capitalize(),
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

    # ------------------------------------------------------------------ role pointers
    def generate_role_pointer(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
        from squads import interactions

        pointer = ctx.paths.claude_dir / "agents" / f"{role.slug}.md"
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
        return Artifact(self._rel(ctx, pointer), "agent", self.name)

    def generate_skill_pointer(self, ctx: BackendContext, item: Item) -> Artifact:
        slug = item.extra.get("slug", item.slug)
        pointer = ctx.paths.claude_dir / "skills" / slug / "SKILL.md"
        pointer.parent.mkdir(parents=True, exist_ok=True)
        description = item.extra.get("description") or item.description or item.title
        pointer.write_text(
            render(
                "claude/pointer_skill.md.j2",
                slug=slug,
                description=oneline(description),
                squad_path=ctx.root_relative(item),
            ),
            encoding="utf-8",
        )
        return Artifact(self._rel(ctx, pointer), "skill_pointer", self.name)

    def remove_artifacts(self, ctx: BackendContext, item: Item) -> None:
        from squads.models import ItemType

        slug = item.extra.get("slug", item.slug)
        if item.type is ItemType.SKILL:
            import shutil

            skill_dir = ctx.paths.claude_dir / "skills" / slug
            if skill_dir.is_dir():
                shutil.rmtree(skill_dir)
        else:
            (ctx.paths.claude_dir / "agents" / f"{slug}.md").unlink(missing_ok=True)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _rel(ctx: BackendContext, path: Path) -> str:
        import os

        return os.path.relpath(path, ctx.root).replace(os.sep, "/")
