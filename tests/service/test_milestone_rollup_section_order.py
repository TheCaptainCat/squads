"""``milestone_rollup``'s accepted member order: within each of the three partitions
(Delivered / Outstanding / Settled without delivering), members sort by type, then by
sequence id — never regrouped by status *role*. Pinned two ways:

1. A fixture milestone whose partitions each mix several status roles (an ``active`` bug next
   to a ``done`` feature, both landing in the same partition together) — the shape that would
   visibly reorder if status-role grouping crept back in. The expected order is computed
   independently, from the same items the fixture created, never hand-typed.
2. The sort is explicitly ``case_sensitive=True`` in the template (ASCII order, matching
   Python's own default string comparison) rather than Jinja's own case-insensitive default —
   otherwise a project's custom, differently-cased item type would sort inconsistently with
   the bundled all-lowercase ones. Covered directly at the render layer, since exercising it
   through a real item type would require declaring one via an override.
"""

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

    # Outstanding: two roles (active, attention) across two types.
    bug_a = (await create_item(svc, "bug", "Bug A")).item
    await svc.add_ref(bug_a.id, m.id, kind="targets")
    await svc.set_status(bug_a.id, "InProgress")  # role: active

    bug_b = (await create_item(svc, "bug", "Bug B")).item
    await svc.add_ref(bug_b.id, m.id, kind="targets")
    # stays Open — role: attention

    feat_c = (await create_item(svc, "feature", "Feat C")).item
    await svc.add_ref(feat_c.id, m.id, kind="targets")
    await svc.set_status(feat_c.id, "Ready")
    await svc.set_status(feat_c.id, "InProgress")  # role: active

    # Delivered: three types, two delivery-terminal roles (done, in_force).
    feat_d = (await create_item(svc, "feature", "Feat D")).item
    await svc.add_ref(feat_d.id, m.id, kind="targets")
    await svc.set_status(feat_d.id, "Ready")
    await svc.set_status(feat_d.id, "InProgress")
    await svc.set_status(feat_d.id, "Done")  # role: done

    dec_g = (await create_item(svc, "decision", "Dec G")).item
    await svc.add_ref(dec_g.id, m.id, kind="targets")
    await svc.set_status(dec_g.id, "Accepted")  # role: in_force

    bug_f = (await create_item(svc, "bug", "Bug F")).item
    await svc.add_ref(bug_f.id, m.id, kind="targets")
    await svc.set_status(bug_f.id, "InProgress")
    await svc.set_status(bug_f.id, "Fixed")
    await svc.set_status(bug_f.id, "Verified")  # role: done

    # Settled without delivering: one member is enough to prove it renders, not a re-partition.
    dec_h = (await create_item(svc, "decision", "Dec H")).item
    await svc.add_ref(dec_h.id, m.id, kind="targets")
    await svc.set_status(dec_h.id, "Accepted")
    await svc.set_status(dec_h.id, "Superseded")  # settled, not delivered

    def _by_type_then_seq(items):
        return [i.id for i in sorted(items, key=lambda i: (i.type, i.sequence_id))]

    expected_order = (
        _by_type_then_seq([bug_f, dec_g, feat_d])  # Delivered
        + _by_type_then_seq([bug_a, bug_b, feat_c])  # Outstanding
        + _by_type_then_seq([dec_h])  # Settled without delivering
    )
    # The fixture is only a meaningful capture if creation order disagrees with the accepted
    # order for at least one partition — otherwise a status-role-grouping regression could pass
    # by accident.
    assert expected_order[:3] != [feat_d.id, dec_g.id, bug_f.id]

    direct = await svc.render_view("milestone_rollup", m.id)
    assert _ids_in_render_order(direct) == expected_order

    tag_driven = await svc.read_body(m.id)
    assert _ids_in_render_order(tag_driven) == expected_order
    # The tag-driven read expands the view inline into the surrounding body prose — the direct
    # render must appear in it verbatim, not merely produce the same member order independently.
    assert direct in tag_driven


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
    """Both fake members share a status with no settled role, so both land in Outstanding and
    the only thing left to decide their order is the type-text comparison itself. Ascending
    ASCII order (case-sensitive) puts an upper-case type before a lower-case one; Jinja's own
    default (case-insensitive) would put them the other way around — this pins the deliberate
    choice, not merely a default nobody looked at."""
    host = await _milestone(svc)
    members = [
        _FakeMember(id="BUG-2", type="bug", status="Draft", title="Bug", sequence_id=2),
        _FakeMember(id="INC-1", type="Incident", status="Draft", title="Incident", sequence_id=1),
    ]

    # A duck-typed stand-in, not a real Item/SubEntity — the template only reads attributes off
    # it, so casting the declared SourceResult is honest here rather than a type escape hatch.
    rendered = views.render_source_view(
        "milestone_rollup", cast(views.SourceResult, members), host, svc.spec, None
    )

    assert "## Outstanding (2)" in rendered
    outstanding = rendered.split("## Outstanding")[1].split("## Settled")[0]
    assert outstanding.index("INC-1") < outstanding.index("BUG-2")
