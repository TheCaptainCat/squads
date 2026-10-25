"""`sq override scaffold --role` writes every overridable field commented out with its bundled
value, plus the append idiom, and each line loads once uncommented."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from _helpers import catalog_of
from squads._overrides import _service as override_service
from squads._overrides._service import scaffold_role
from squads._roles._catalog import role_by_slug
from squads._roles._models import RoleSpec
from squads._roles._resolver import resolve_role

pytestmark = pytest.mark.anyio

_FIELD_LINE = re.compile(r"^# (\w+) = ", re.MULTILINE)
_SPLAT_LINE = '# responsibilities = ["$(*self)", "…"]'
_NOT_OVERRIDABLE = {"slug", "is_default"}
_OVERRIDABLE = [f for f in RoleSpec.model_fields if f not in _NOT_OVERRIDABLE]


def _scaffold(project, slug: str) -> tuple[str, Path]:
    dest = scaffold_role(project.squad_dir, slug)
    return dest.read_text(encoding="utf-8"), dest


def _field_lines(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if _FIELD_LINE.match(ln) and ln != _SPLAT_LINE]


def _uncomment(line: str) -> str:
    return line.removeprefix("# ")


async def test_the_commented_fields_are_exactly_the_overridable_role_fields(project) -> None:
    text, _ = _scaffold(project, "tech-lead")
    assert set(_FIELD_LINE.findall(text)) == set(_OVERRIDABLE)
    assert len(_field_lines(text)) == len(_OVERRIDABLE)


@pytest.mark.parametrize("field", _OVERRIDABLE)
async def test_each_line_uncommented_alone_loads_as_the_bundled_value(project, field: str) -> None:
    text, dest = _scaffold(project, "tech-lead")
    line = next(ln for ln in _field_lines(text) if ln.startswith(f"# {field} = "))
    dest.write_text(text.replace(line, _uncomment(line)), encoding="utf-8")
    assert resolve_role(
        "tech-lead", project.squad_dir, catalog=catalog_of(project.squad_dir)
    ) == role_by_slug("tech-lead")


@pytest.mark.parametrize("slug", ["tech-lead", "qa"])
async def test_the_whole_scaffold_uncommented_loads_as_the_bundled_role(project, slug: str) -> None:
    text, dest = _scaffold(project, slug)
    for line in _field_lines(text):
        text = text.replace(line, _uncomment(line))
    dest.write_text(text, encoding="utf-8")
    assert resolve_role(
        slug, project.squad_dir, catalog=catalog_of(project.squad_dir)
    ) == role_by_slug(slug)


async def test_a_field_the_bundled_role_leaves_unset_has_no_line(project, monkeypatch) -> None:
    bare = replace(role_by_slug("qa"), model=None, color=None)
    monkeypatch.setattr(override_service, "role_by_slug", lambda _slug: bare)
    text, _ = _scaffold(project, "qa")
    assert set(_FIELD_LINE.findall(text)) == set(_OVERRIDABLE) - {"model", "color"}


async def test_the_append_line_resolves_to_the_bundled_list_plus_the_new_entry(project) -> None:
    text, dest = _scaffold(project, "tech-lead")
    assert _SPLAT_LINE in text
    dest.write_text(text.replace(_SPLAT_LINE, _uncomment(_SPLAT_LINE)), encoding="utf-8")
    assert resolve_role(
        "tech-lead", project.squad_dir, catalog=catalog_of(project.squad_dir)
    ).responsibilities == (
        *role_by_slug("tech-lead").responsibilities,
        "…",
    )
