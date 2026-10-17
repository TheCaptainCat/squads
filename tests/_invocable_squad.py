"""A seeded squad holding one skill of every shape the skill-invocability tests range over."""

import json
from pathlib import Path
from typing import Any

from squads import __version__
from squads._paths import SquadPaths
from squads._services import _service as service

#: Skill shape -> the slug it is exercised under, and the value its declaration resolves to.
SHAPES: dict[str, tuple[str, bool]] = {
    "always-on squads": ("squads", False),
    "always-on memory": ("sq-memory", False),
    "always-on greeting": ("greeting", False),
    "bundled type": ("sq-task", False),
    "declared type": ("sq-incident", False),
    "authored": ("onboarding", True),
    "authored sq-prefixed": ("sq-onboarding", True),
}

_INCIDENT_OVERRIDE = """\
[lifecycles.triage]
initial = "Open"
[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
"""

SYSTEM_SLUGS = [slug for slug, declared in SHAPES.values() if not declared]


async def build_squad(tmp_path: Path, monkeypatch, invoke) -> SquadPaths:
    """Init with skill seeding, declare an ``incident`` type, add two authored skills, sync."""
    monkeypatch.chdir(tmp_path)
    paths = (await service.init(root=tmp_path, roles_spec="minimal")).paths
    overrides = paths.squad_dir / ".overrides"
    overrides.mkdir(parents=True, exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{_INCIDENT_OVERRIDE}", encoding="utf-8"
    )
    for name in ("onboarding", "sq-onboarding"):
        r = await invoke(["skill", "add", name])
        assert r.exit_code == 0, r.output
    r = await invoke(["sync"])
    assert r.exit_code == 0, r.output
    return paths


def pointer(paths: SquadPaths, slug: str) -> str:
    return (paths.root / ".claude" / "skills" / slug / "SKILL.md").read_text(encoding="utf-8")


def pointer_lines(paths: SquadPaths, slug: str) -> list[str]:
    """The pointer's frontmatter lines between the two ``---`` fences."""
    return pointer(paths, slug).split("---\n")[1].splitlines()


async def drifted(invoke) -> list[str]:
    """The pointer paths ``sq check`` reports as drifted."""
    r = await invoke(["check", "--json"])
    return sorted(i["item"] for i in json.loads(r.stdout) if "had drifted" in i["message"])


async def skill_show(invoke, slug: str) -> dict[str, Any]:
    r = await invoke(["skill", slug, "show", "--json"])
    assert r.exit_code == 0, r.output
    return json.loads(r.stdout)
