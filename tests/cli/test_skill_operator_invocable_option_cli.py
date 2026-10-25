"""``--operator-invocable <yes|no|default>`` on ``sq skill add`` and ``sq skill <addr> update``:
yes and no store the value even when it equals the default, default removes it, leaving it out
changes nothing, and any other text is refused with nothing written. A table over verb by value
by skill shape, then the stored value's life across sync, index loss and a release."""

from types import MappingProxyType

import pytest

from _helpers import make_service, squad_tree
from _invocable_squad import SHAPES, build_squad, pointer_lines, skill_show
from squads._interactions import _skills as skills
from squads._interactions._skills import OPERATOR_INVOCABLE_DEFAULTS
from squads._sections import split_frontmatter

pytestmark = pytest.mark.anyio

LINE = "user-invocable: false"
KEY = "operator_invocable"

#: (value text or None for omitted, stored result, accepted)
VALUES = [
    ("yes", True, True),
    ("no", False, True),
    ("default", None, True),
    (None, None, True),
    ("Yes", None, False),
    ("false", None, False),
    ("", None, False),
]
VALUE_IDS = ["yes", "no", "default", "omitted", "Yes", "false", "empty"]


def _stored(paths, svc_item_path: str) -> object:
    text = paths.abspath(svc_item_path).read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    return (fm or {}).get(KEY)


async def _item_path(paths, slug: str) -> str:
    item = await make_service(paths).roster_item("skill", slug)
    assert item is not None
    return item.path


def _args(value: str | None) -> list[str]:
    return [] if value is None else ["--operator-invocable", value]


@pytest.mark.parametrize("text,stored,accepted", VALUES, ids=VALUE_IDS)
@pytest.mark.parametrize("shape", SHAPES)
async def test_update_by_value_and_shape(
    shape, text, stored, accepted, tmp_path, monkeypatch, invoke
) -> None:
    slug, declared = SHAPES[shape]
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    before = squad_tree(paths.root)

    r = await invoke(["skill", slug, "update", *_args(text)])

    if not accepted or text is None:  # omitted leaves `update` with nothing to change
        assert r.exit_code == 1, r.output
        assert ("yes, no or default" in r.output) is (text is not None)
        assert squad_tree(paths.root) == before
        return
    assert r.exit_code == 0, r.output
    assert _stored(paths, await _item_path(paths, slug)) == stored
    resolved = declared if stored is None else stored
    assert (LINE in pointer_lines(paths, slug)) is (not resolved)
    row = await skill_show(invoke, slug)
    assert row["operator_invocable"] is resolved
    assert row["operator_invocable_set"] is (stored is not None)


@pytest.mark.parametrize("text,stored,accepted", VALUES, ids=VALUE_IDS)
@pytest.mark.parametrize("name", ["fresh", "sq-fresh"])
async def test_add_by_value_and_shape(
    name, text, stored, accepted, tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    before = squad_tree(paths.root)

    r = await invoke(["skill", "add", name, *_args(text)])

    if not accepted:
        assert r.exit_code == 1, r.output
        assert "yes, no or default" in r.output
        assert squad_tree(paths.root) == before
        return
    assert r.exit_code == 0, r.output
    assert _stored(paths, await _item_path(paths, name)) == stored
    resolved = True if stored is None else stored
    assert (LINE in pointer_lines(paths, name)) is (not resolved)


async def test_a_system_skill_accepts_only_this_option(tmp_path, monkeypatch, invoke) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    r = await invoke(["skill", "sq-task", "update", "--operator-invocable", "yes"])
    assert r.exit_code == 0, r.output
    assert LINE not in pointer_lines(paths, "sq-task")
    before = squad_tree(paths.root)
    for refused in (["--title", "x"], ["--desc", "x"], ["--when-to-use", "x"]):
        r = await invoke(["skill", "sq-task", "update", *refused, "--operator-invocable", "no"])
        assert r.exit_code == 1, r.output
    assert squad_tree(paths.root) == before


async def test_a_stored_value_survives_sync_and_an_index_rebuild(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    for slug, text in (("squads", "yes"), ("onboarding", "no")):
        r = await invoke(["skill", slug, "update", "--operator-invocable", text])
        assert r.exit_code == 0, r.output
    assert (await invoke(["sync"])).exit_code == 0
    paths.index_path.unlink()
    r = await invoke(["repair"])
    assert r.exit_code == 0, r.output
    squads = await skill_show(invoke, "squads")
    onboarding = await skill_show(invoke, "onboarding")
    assert (squads["operator_invocable"], squads["operator_invocable_set"]) == (True, True)
    assert (onboarding["operator_invocable"], onboarding["operator_invocable_set"]) == (False, True)


async def test_a_release_changing_a_default_moves_only_skills_with_no_stored_value(
    tmp_path, monkeypatch, invoke
) -> None:
    paths = await build_squad(tmp_path, monkeypatch, invoke)
    assert (
        await invoke(["skill", "greeting", "update", "--operator-invocable", "no"])
    ).exit_code == 0
    assert LINE in pointer_lines(paths, "squads")
    flipped = {slug: True for slug in OPERATOR_INVOCABLE_DEFAULTS}
    monkeypatch.setattr(skills, "OPERATOR_INVOCABLE_DEFAULTS", MappingProxyType(flipped))
    monkeypatch.setattr(skills, "ITEM_SKILL_OPERATOR_INVOCABLE", True)

    assert (await invoke(["sync"])).exit_code == 0

    for moved in ("squads", "sq-memory", "sq-task", "sq-incident"):
        assert LINE not in pointer_lines(paths, moved), moved
    assert LINE in pointer_lines(paths, "greeting")  # the squad's own choice is kept
