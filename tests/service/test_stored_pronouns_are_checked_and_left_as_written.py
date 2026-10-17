"""A stored ``pronouns`` that fails the shape rule is reported by ``sq check`` on a role and on an
operator, and every surface leaves the file as written: ``sq check`` and ``sq repair`` never
rewrite it, and ``--set`` cannot replace it. One table over the stored shapes crosses the check,
the loaded value and the rebuilt index."""

from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._models._attributes import AttributeKey
from squads._pronouns import pronouns
from squads._rendering._engine import invalidate_squad_dir
from squads._sections import replace_frontmatter, split_frontmatter
from squads._services._service import Service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

# (id, stored frontmatter value, reported by the pronouns check)
STORED: list[tuple[str, Any, bool]] = [
    ("slash-pair", "they/them", False),
    ("one-character", "x", False),
    ("forty-characters", "a" * 40, False),
    ("forty-one-characters", "a" * 41, True),
    ("surrounding-whitespace", "  they/them ", False),
    ("empty", "", True),
    ("whitespace-only", "   ", True),
    ("embedded-newline", "they/\nthem", True),
    ("embedded-tab", "they/\tthem", True),
    ("other-control-character", "they\x07them", True),
    ("bidi-override", f"they{chr(0x202E)}them", True),
    ("zero-width-space", f"they{chr(0x200B)}them", True),
    ("forty-one-decomposed-accents", "e\u0301" * 41, True),
    ("forty-decomposed-accents", "e\u0301" * 40, False),
    ("marker-tag", "<!-- sq:body -->", True),
    ("square-brackets", "[x]", False),
    ("non-ascii", "elle/iel", False),
    ("null", None, False),
    ("list", ["they/them"], False),
    ("integer", 5, False),
]


async def _roster_entry(svc: Service, kind: str) -> Any:
    if kind == "role":
        return await svc.activate_role("architect")
    return await svc.add_operator("Alex Rivera")


async def _store(svc: Service, item: Any, value: Any) -> tuple[Path, bytes]:
    path = svc.paths.abspath(item.path)
    text = path.read_text(encoding="utf-8")
    data, _ = split_frontmatter(text)
    data[AttributeKey.PRONOUNS] = value
    path.write_text(replace_frontmatter(text, data), encoding="utf-8")
    await svc.repair()
    return path, path.read_bytes()


@pytest.mark.parametrize("kind", ["role", "operator"])
@pytest.mark.parametrize(("shape", "value", "reported"), STORED, ids=[s[0] for s in STORED])
async def test_check_reports_a_failing_stored_value_and_leaves_the_file_as_written(
    svc: Service, kind: str, shape: str, value: Any, reported: bool
) -> None:
    item = await _roster_entry(svc, kind)
    path, before = await _store(svc, item, value)

    issues = [i for i in await svc.check() if i.item == item.id and "pronouns" in i.message]
    shape_issues = [i for i in issues if i.message.startswith("pronouns ")]

    if reported:
        assert [i.level for i in shape_issues] == ["error"]
        assert f"sq {kind} {item.slug} update --pronouns" in shape_issues[0].message
    else:
        assert shape_issues == []
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", ["role", "operator"])
@pytest.mark.parametrize(("shape", "value", "reported"), STORED, ids=[s[0] for s in STORED])
async def test_the_rebuilt_index_carries_the_stored_value_verbatim(
    svc: Service, kind: str, shape: str, value: Any, reported: bool
) -> None:
    item = await _roster_entry(svc, kind)
    await _store(svc, item, value)

    rebuilt = await svc.get(item.id)

    assert rebuilt.attributes[AttributeKey.PRONOUNS] == value
    assert (pronouns(rebuilt) is None) is (reported or not isinstance(value, str))


@pytest.mark.parametrize("kind", ["role", "operator"])
async def test_set_cannot_write_pronouns_and_names_the_verb(svc: Service, kind: str) -> None:
    item = await _roster_entry(svc, kind)
    path = svc.paths.abspath(item.path)
    before = path.read_bytes()

    with pytest.raises(SquadsError, match=r"update --pronouns"):
        await svc.update(item.id, set_attributes={AttributeKey.PRONOUNS: "they/them"})
    with pytest.raises(SquadsError, match=r"update --pronouns"):
        await svc.update(item.id, unset_attributes=[AttributeKey.PRONOUNS])

    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", ["role", "operator"])
async def test_an_override_that_re_kinds_pronouns_is_refused_at_load_naming_the_key(
    project: Any, kind: str
) -> None:
    overrides = project.squad_dir / ".overrides"
    overrides.mkdir(exist_ok=True)
    (overrides / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        f'[items.{kind}.attributes]\npronouns = {{ kind = "list" }}\n',
        encoding="utf-8",
    )
    invalidate_squad_dir(project.squad_dir)

    with pytest.raises(SquadsError, match=rf"{kind}.*pronouns"):
        load_workflow_spec(squad_dir=project.squad_dir)


@pytest.mark.parametrize("kind", ["role", "operator"])
def test_the_bundled_spec_declares_pronouns_as_an_unsettable_string(kind: str) -> None:
    spec = load_workflow_spec()

    declared = spec.item_attributes(kind)[AttributeKey.PRONOUNS]

    assert (declared.kind, declared.settable, declared.required) == ("str", False, False)
