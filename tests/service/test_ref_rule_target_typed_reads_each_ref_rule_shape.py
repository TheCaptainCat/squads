"""`ref_rule_target_typed` over the shapes of a type's ref rules and edges: only a rule that
declares a target counts, an untyped rule neither checks its kind nor widens a typed rule, a
bare edge is the default kind, a dangling target is left to `dangling_ref`, and each misdirected
edge earns exactly one finding that names the edge, its kind, the type it reaches and the types
the rule accepts.
"""

from dataclasses import dataclass

import pytest

from _helpers import create_item
from _selection_table import (
    DECLARED_ROWS,
    REF_RULE_TARGET_TYPED,
    member_findings,
    service_with,
)

pytestmark = pytest.mark.anyio

_SELECT = 'validators = ["ref_rule_target_typed"]\n'
_DECLARED_KIND = '[ref_kinds.audits]\nlabel = "Audits"\nhint = "A audits B"\n'
_INCIDENT = DECLARED_ROWS[0].declaration


@dataclass(frozen=True)
class Case:
    toml: str
    #: (target type, kind as spelled on `ref add`, "" for bare) per edge, in creation order.
    edges: tuple[tuple[str, str], ...]
    #: Which of those edges are reported, as indexes into *edges*.
    reported: tuple[int, ...]
    #: The accepted types the message of a reported edge lists.
    accepted: str


_CASES: dict[str, Case] = {
    "bundled-feature-rule": Case(
        f"[items.feature]\n{_SELECT}",
        (("task", "implements"), ("contract", "implements"), ("decision", "implements")),
        (0, 2),
        "contract",
    ),
    "two-typed-rules-of-one-kind": Case(
        '[items.feature]\nref_rules = [{ kind = "implements", target = "contract" },'
        f' {{ kind = "implements", target = "milestone" }}]\n{_SELECT}',
        (
            ("contract", "implements"),
            ("milestone", "implements"),
            ("task", "implements"),
        ),
        (2,),
        "contract/milestone",
    ),
    "a-typed-and-an-untyped-rule-of-one-kind": Case(
        '[items.feature]\nref_rules = [{ kind = "implements", target = "contract" },'
        f' {{ kind = "implements" }}]\n{_SELECT}',
        (("task", "implements"), ("contract", "implements")),
        (0,),
        "contract",
    ),
    "an-untyped-rule-alone-checks-nothing": Case(
        '[items.feature]\nref_rules = [{ kind = "implements", target = "contract" },'
        f' {{ kind = "addresses" }}]\n{_SELECT}',
        (("task", "addresses"), ("task", "implements")),
        (1,),
        "contract",
    ),
    "a-kind-with-no-rule": Case(
        f"[items.feature]\n{_SELECT}",
        (("task", "depends-on"), ("task", "targets"), ("task", "")),
        (),
        "",
    ),
    "a-typed-rule-on-the-default-kind": Case(
        f'[items.feature]\nref_rules = [{{ kind = "related", target = "milestone" }}]\n{_SELECT}',
        (
            ("task", ""),
            ("task", "related"),
            ("milestone", ""),
            ("milestone", "related"),
        ),
        (0, 1),
        "milestone",
    ),
    "a-declared-kind-and-a-declared-type": Case(
        f"{_DECLARED_KIND}[items.incident]\n{_INCIDENT}\n[items.feature]\n"
        f'ref_rules = [{{ kind = "audits", target = "incident" }}]\n{_SELECT}',
        (("task", "audits"), ("incident", "audits")),
        (0,),
        "incident",
    ),
}


@pytest.mark.parametrize("case", _CASES)
async def test_each_misdirected_edge_earns_one_finding_and_no_other_edge_does(
    project, case: str
) -> None:
    spec = _CASES[case]
    svc = service_with(project.squad_dir, spec.toml)
    source = (await create_item(svc, "feature", "source")).item
    targets: list[str] = []
    for target_type, kind in spec.edges:
        target = (await create_item(svc, target_type, f"{target_type} target")).item
        await svc.add_ref(source.id, target.id, kind=kind)
        targets.append(target.id)

    found = member_findings(await svc.check(), REF_RULE_TARGET_TYPED)
    assert [item for _, item, _ in found] == [source.id] * len(spec.reported)
    for finding, index in zip(found, spec.reported, strict=True):
        target_type, kind = spec.edges[index]
        resolved = kind or "related"
        assert finding[0] == "warn"
        assert finding[2] == (
            f"{resolved} edge to {targets[index]} points at a {target_type}, but a feature's "
            f"{resolved} refs must point at a {spec.accepted}"
        )


async def test_a_dangling_target_is_left_to_the_dangling_ref_check(project) -> None:
    svc = service_with(project.squad_dir, f"[items.feature]\n{_SELECT}")
    source = (await create_item(svc, "feature", "source", refs=["TASK-999999:implements"])).item
    issues = [i for i in await svc.check() if i.item == source.id]
    assert [i.message for i in issues] == ["dangling ref TASK-999999"]
    assert member_findings(issues, REF_RULE_TARGET_TYPED) == []


async def test_three_misdirected_edges_earn_three_findings(project) -> None:
    svc = service_with(project.squad_dir, f"[items.feature]\n{_SELECT}")
    source = (await create_item(svc, "feature", "source")).item
    for index in range(3):
        target = (await create_item(svc, "task", f"target {index}")).item
        await svc.add_ref(source.id, target.id, kind="implements")
    found = member_findings(await svc.check(), REF_RULE_TARGET_TYPED)
    assert len(found) == 3
    assert len({message for _, _, message in found}) == 3
