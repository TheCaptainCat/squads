"""``milestone_rollup``'s accepted member order sorts by type then sequence id within each
partition, never regrouped by status role, and the type sort is ASCII case-sensitive."""

import re
from dataclasses import dataclass
from typing import cast

import pytest

from _helpers import create_item
from squads import _views as views

pytestmark = pytest.mark.anyio

_ID_RE = re.compile(r"\*\*([A-Za-z][\w-]*-\d+)\*\*")


def _ids_in_render_order(text: str) -> list[str]:
    return _ID_RE.findall(text)


async def _milestone(svc, **kwargs):
    return (await create_item(svc, "milestone", "Ship the release", **kwargs)).item


# --------------------------------------------------------------------------- type/seq order


async def test_each_partition_orders_by_type_then_sequence_id_across_mixed_status_roles(
    project, svc
) -> None:
    m = await _milestone(svc)

    bug_a = (await create_item(svc, "bug", "Bug A")).item
    await svc.add_ref(bug_a.id, m.id, kind="targets")
    await svc.set_status(bug_a.id, "InProgress")

    bug_b = (await create_item(svc, "bug", "Bug B")).item
    await svc.add_ref(bug_b.id, m.id, kind="targets")

    feat_c = (await create_item(svc, "feature", "Feat C")).item
    await svc.add_ref(feat_c.id, m.id, kind="targets")
    await svc.set_status(feat_c.id, "Ready")
    await svc.set_status(feat_c.id, "InProgress")

    feat_d = (await create_item(svc, "feature", "Feat D")).item
    await svc.add_ref(feat_d.id, m.id, kind="targets")
    await svc.set_status(feat_d.id, "Ready")
    await svc.set_status(feat_d.id, "InProgress")
    await svc.set_status(feat_d.id, "Done")

    dec_g = (await create_item(svc, "decision", "Dec G")).item
    await svc.add_ref(dec_g.id, m.id, kind="targets")
    await svc.set_status(dec_g.id, "Accepted")

    bug_f = (await create_item(svc, "bug", "Bug F")).item
    await svc.add_ref(bug_f.id, m.id, kind="targets")
    await svc.set_status(bug_f.id, "InProgress")
    await svc.set_status(bug_f.id, "Fixed")
    await svc.set_status(bug_f.id, "Verified")

    dec_h = (await create_item(svc, "decision", "Dec H")).item
    await svc.add_ref(dec_h.id, m.id, kind="targets")
    await svc.set_status(dec_h.id, "Accepted")
    await svc.set_status(dec_h.id, "Superseded")

    def _by_type_then_seq(items):
        return [i.id for i in sorted(items, key=lambda i: (i.type, i.sequence_id))]

    expected_order = (
        _by_type_then_seq([bug_f, dec_g, feat_d])
        + _by_type_then_seq([bug_a, bug_b, feat_c])
        + _by_type_then_seq([dec_h])
    )
    assert expected_order[:3] != [feat_d.id, dec_g.id, bug_f.id]

    direct = await svc.render_view("milestone_rollup", m.id)
    assert _ids_in_render_order(direct) == expected_order

    tag_driven = await svc.read_body(m.id)
    assert _ids_in_render_order(tag_driven) == expected_order
    assert direct.strip("\n") in tag_driven


# --------------------------------------------------------------------------- case sensitivity


@dataclass
class _FakeMember:
    id: str
    type: str
    status: str
    title: str
    sequence_id: int
    assignee: str | None = None


async def test_the_type_sort_is_case_sensitive_not_jinjas_case_insensitive_default(
    project, svc
) -> None:
    """Ascending ASCII order puts an upper-case type before a lower-case one, unlike Jinja's
    own case-insensitive default."""
    host = await _milestone(svc)
    members = [
        _FakeMember(id="BUG-2", type="bug", status="Draft", title="Bug", sequence_id=2),
        _FakeMember(id="INC-1", type="Incident", status="Draft", title="Incident", sequence_id=1),
    ]

    rendered = views.render_source_view(
        "milestone_rollup", cast(views.SourceResult, members), host, svc.spec, None
    )

    assert "## Outstanding (2)" in rendered
    outstanding = rendered.split("## Outstanding")[1].split("## Settled")[0]
    assert outstanding.index("INC-1") < outstanding.index("BUG-2")
