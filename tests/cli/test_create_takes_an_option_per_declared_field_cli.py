"""`sq create <type>` takes one `--<field-code>` option per field the type declares in the active
spec, bundled or override-declared; `--priority` stays the flag for the priority field."""

import json
from pathlib import Path

import pytest

from squads._services._service import open_service

pytestmark = pytest.mark.anyio

_OVERRIDE = """\
[collections.level]
label = "Level"
ordered = true
badges = [
  { code = "high", label = "High", emoji = "H" },
  { code = "low", label = "Low", emoji = "L" },
]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
fields = [{ code = "impact", label = "Impact", collection = "level" }]

[items.task]
fields = [
  { code = "priority", label = "Priority", collection = "priority" },
  { code = "impact", label = "Impact", collection = "level" },
]
"""


def _write_override(squad_dir: Path) -> None:
    (squad_dir / ".overrides").mkdir(parents=True, exist_ok=True)
    (squad_dir / ".overrides" / "workflow.toml").write_text(_OVERRIDE, encoding="utf-8")


# (type, extra args, field, expected stored code)
ACCEPTED = {
    "bug severity": ("bug", ["--severity", "high"], "severity", "high"),
    "bug priority": ("bug", ["--priority", "urgent"], "priority", "urgent"),
    "override field on a custom type": ("incident", ["--impact", "low"], "impact", "low"),
    "override field on a bundled type": ("task", ["--impact", "high"], "impact", "high"),
}


@pytest.mark.parametrize("case", list(ACCEPTED))
async def test_a_declared_field_option_stores_its_value(project, invoke, case) -> None:
    item_type, extra, field, expected = ACCEPTED[case]
    _write_override(project.squad_dir)

    result = await invoke(["create", item_type, "T", "--author", "manager", "--json", *extra])

    assert result.exit_code == 0, result.output
    stored = await open_service().get(json.loads(result.stdout)["id"])
    assert stored.badge_value(field) == expected


REFUSED = {
    "a code outside the collection": ("bug", ["--severity", "nope"], "invalid severity"),
    "a field the type does not declare": ("task", ["--severity", "high"], "No such option"),
}


@pytest.mark.parametrize("case", list(REFUSED))
async def test_a_bad_field_option_is_refused_and_creates_nothing(project, invoke, case) -> None:
    item_type, extra, message = REFUSED[case]
    before = sorted(p.name for p in project.squad_dir.rglob("*.md"))

    result = await invoke(["create", item_type, "T", "--author", "manager", *extra])

    assert result.exit_code != 0
    assert message in result.output
    assert sorted(p.name for p in project.squad_dir.rglob("*.md")) == before
