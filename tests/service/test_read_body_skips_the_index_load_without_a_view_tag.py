"""``Service.read_body`` skips the second, expansion-only index load when the body carries no
``sq:view:<name>`` tag, asserted by call count since a result-only check cannot tell the
skipped load apart from one that happened."""

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio

_BUNDLED_VIEW = "milestone_rollup"


def _count_loads(monkeypatch, svc) -> list[int]:
    """Wrap ``svc.store.load`` to count calls, returning a running counter list."""
    calls = [0]
    original = svc.store.load

    async def counted(*args, **kwargs):
        calls[0] += 1
        return await original(*args, **kwargs)

    monkeypatch.setattr(svc.store, "load", counted)
    return calls


async def test_read_body_makes_one_load_call_for_a_body_with_no_tag(svc, monkeypatch) -> None:
    task = (await create_item(svc, "task", "T", body="Plain prose, no tag at all.")).item

    calls = _count_loads(monkeypatch, svc)
    body = await svc.read_body(task.id)

    assert body == "Plain prose, no tag at all."
    assert calls[0] == 1, "read_body must not load the index a second time for a tagless body"


async def test_read_body_makes_two_load_calls_for_a_body_carrying_a_tag(svc, monkeypatch) -> None:
    task = (await create_item(svc, "task", "T")).item
    await svc.add_view(task.id, _BUNDLED_VIEW)
    expected = (await svc.render_view(_BUNDLED_VIEW, task.id)).strip()

    calls = _count_loads(monkeypatch, svc)
    body = await svc.read_body(task.id)

    assert expected in body
    assert f"sq:view:{_BUNDLED_VIEW}" not in body
    assert calls[0] == 2, "read_body must load the index a second time to expand a tagged body"


async def test_read_body_result_is_unchanged_whether_or_not_the_load_is_skipped(svc) -> None:
    """A tagless body and a tagged body's expansion are unchanged whether or not the load
    is skipped."""
    plain = (await create_item(svc, "task", "T", body="Untagged body.")).item
    assert await svc.read_body(plain.id) == "Untagged body."

    tagged = (await create_item(svc, "task", "T2")).item
    await svc.add_view(tagged.id, _BUNDLED_VIEW)
    expected = (await svc.render_view(_BUNDLED_VIEW, tagged.id)).strip()
    rendered = await svc.read_body(tagged.id)
    assert expected in rendered
    assert f"sq:view:{_BUNDLED_VIEW}" not in rendered
