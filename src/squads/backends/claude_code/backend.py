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
        # squads skill
        skill = ctx.paths.claude_dir / "skills" / "squads" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text(
            render("claude/squads_skill.md.j2", version=ctx.version, squad_dir=squad_dir),
            encoding="utf-8",
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
        return [
            Artifact(self._rel(ctx, skill), "skill", self.name),
            Artifact(self._rel(ctx, ctx.paths.claude_md), "claude_md", self.name),
        ]

    # ------------------------------------------------------------------ role pointers
    def generate_role_pointer(self, ctx: BackendContext, item: Item, role: RoleDef) -> Artifact:
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
