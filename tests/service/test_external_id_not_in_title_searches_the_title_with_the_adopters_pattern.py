"""`external_id_not_in_title:<regex>` over pattern and title shapes: the pattern is searched (not
fully matched) with no flags, so the key may sit at the start, middle or end of the title, an
anchor restricts it, inline flags work, an alternation covers several trackers, and a title with
two keys earns one finding naming the first. The pattern runs on every `check()` for a type that
selects it, and on a gated write only where that type selects it at `@error`.
"""

import pytest

from _helpers import create_item
from _selection_table import (
    EXTERNAL_ID_NOT_IN_TITLE,
    TRACKER_KEY,
    TypeRow,
    member_findings,
    override_toml,
    service_with,
)
from squads._errors import SquadsError
from squads._services import _validators as validators

pytestmark = pytest.mark.anyio

_TASK = TypeRow("task", "task")
_NAME = "external_id_not_in_title"

#: Pattern -> [(title, the text the finding names, or None when the title is clean)].
_SHAPES: dict[str, list[tuple[str, str | None]]] = {
    TRACKER_KEY: [
        ("Fix ABC-123 flake", "ABC-123"),
        ("ABC-123 at the start", "ABC-123"),
        ("at the end ABC-123", "ABC-123"),
        ("Fix the flake", None),
        ("abc-123 in lower case", None),
        ("two keys ABC-1 and DEF-2", "ABC-1"),
    ],
    r"^[A-Z]+-\d+": [("ABC-1 at the start", "ABC-1"), ("not at the start ABC-1", None)],
    r"[A-Z]+:\d+": [("colon pattern ABC:12 used whole", "ABC:12"), ("ABC-12", None)],
    r"\x40[a-z]+": [("ping @bob about it", "@bob"), ("no handle here", None)],
    r"(?i)abc-\d+": [("lower case abc-123 key", "abc-123"), ("no key", None)],
    r"[A-Z]+-\d+|GH#\d+": [("a tracker ABC-1", "ABC-1"), ("a hash GH#42", "GH#42"), ("none", None)],
    r"\[[A-Z]+-\d+\]": [("[ABC-1] bracketed", "[ABC-1]"), ("ABC-1 bare", None)],
}
_CASES = [(p, t, m) for p, titles in _SHAPES.items() for t, m in titles]


@pytest.mark.parametrize(
    ("pattern", "title", "named"), _CASES, ids=[f"{p}|{t}" for p, t, _ in _CASES]
)
async def test_a_title_is_reported_naming_the_first_match_exactly_when_the_pattern_finds_one(
    project, pattern: str, title: str, named: str | None
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, (f"{_NAME}:{pattern}",)))
    item = (await create_item(svc, "task", title)).item
    found = member_findings(await svc.check(), EXTERNAL_ID_NOT_IN_TITLE)
    if named is None:
        assert found == []
        return
    assert found == [
        (
            "warn",
            item.id,
            f"title holds `{named}` (matches the external-id pattern `{pattern}`)"
            " — keep tracker ids out of the title",
        )
    ]


@pytest.mark.parametrize("splat", [False, True], ids=["replaced", "spliced"])
async def test_an_epic_list_replaced_without_the_splat_form_loses_its_bundled_parent_rule(
    project, splat: bool
) -> None:
    row = TypeRow("epic", "epic")
    svc = service_with(
        project.squad_dir, override_toml(row, (f"{_NAME}:{TRACKER_KEY}",), splat=splat)
    )
    feature = (await create_item(svc, "feature", "f")).item
    if splat:
        with pytest.raises(SquadsError, match="takes no parent"):
            await create_item(svc, "epic", "ABC-1", parent=feature.id)
        epic = (await create_item(svc, "epic", "ABC-1")).item
    else:
        epic = (await create_item(svc, "epic", "ABC-1", parent=feature.id)).item
    assert [i for _, i, _ in member_findings(await svc.check(), EXTERNAL_ID_NOT_IN_TITLE)] == [
        epic.id
    ]


def _count_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []
    real = validators.CATALOG[_NAME]

    def counted(ctx):
        calls.append(ctx.item.id)
        return real(ctx)

    monkeypatch.setitem(validators.CATALOG, _NAME, counted)
    return calls


@pytest.mark.parametrize(("suffix", "gated"), [("", False), ("@warn", False), ("@error", True)])
async def test_the_pattern_runs_on_every_check_and_on_a_gated_write_only_at_error(
    project, monkeypatch: pytest.MonkeyPatch, suffix: str, gated: bool
) -> None:
    svc = service_with(project.squad_dir, override_toml(_TASK, (f"{_NAME}:{TRACKER_KEY}{suffix}",)))
    calls = _count_calls(monkeypatch)
    first = (await create_item(svc, "task", "plain title")).item
    second = (await create_item(svc, "task", "another title")).item
    assert bool(calls) is gated
    calls.clear()
    await svc.update(first.id, add_labels=["touched"])
    assert (calls == [first.id]) is gated

    calls.clear()
    await svc.check()
    assert sorted(calls) == sorted([first.id, second.id])
