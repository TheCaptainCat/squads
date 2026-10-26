"""``agent_registered`` accepts an author or assignee that is a role or an operator, live or
retired, and reports a skill's slug or an unknown one: a skill is outside the author namespace."""

import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
async def roster(svc):
    """One of each kind of roster entry beside the minimal squad's roles."""
    dev = await svc.activate_role(None, from_template="dev", tech="python")
    await svc.add_operator("Anna Lee")
    await svc.add_operator("Old Hand")
    await svc.add_skill("Pairing")
    qa = await svc.activate_role("qa")
    await svc.set_roster_status(qa.id, "Archived")
    old = await svc.roster_item("operator", "op-old")
    await svc.set_roster_status(old.id, "Archived")
    return dev


CASES = [
    pytest.param("manager", True, id="role"),
    pytest.param("python-dev", True, id="developer-role"),
    pytest.param("op-anna", True, id="operator"),
    pytest.param("qa", True, id="retired-role"),
    pytest.param("op-old", True, id="retired-operator"),
    pytest.param("pairing", False, id="skill"),
    pytest.param("ghost", False, id="unknown"),
]


@pytest.mark.parametrize("field", ["author", "assignee"])
@pytest.mark.parametrize(("slug", "registered"), CASES)
async def test_a_slug_is_registered_when_a_role_or_an_operator_holds_it(
    svc, roster, field, slug, registered
) -> None:
    task = (await svc.create("task", "Target", author="manager")).item
    async with svc.store.transaction() as db:  # a hand-edited file reaches the index this way
        setattr(db.get(task.id), field, slug)

    issues = [
        i
        for i in await svc.check()
        if i.item == task.id and "is not a registered role or operator" in i.message
    ]

    assert bool(issues) is not registered
    if issues:
        assert f"{field} '{slug}' is not a registered role or operator" in issues[0].message


async def test_a_skill_item_authored_by_its_own_slug_is_not_reported(svc, roster) -> None:
    issues = await svc.check()

    assert [i for i in issues if "is not a registered role or operator" in i.message] == []


@pytest.mark.parametrize(("author", "reported"), [("pairing", False), ("qa-gone", True)])
async def test_a_skill_authored_by_another_slug_is_exempt_only_when_that_slug_is_registered(
    svc, roster, author, reported
) -> None:
    skill = await svc.roster_item("skill", "pairing")
    async with svc.store.transaction() as db:
        db.get(skill.id).author = author

    issues = [
        i
        for i in await svc.check()
        if i.item == skill.id and "author" in i.message and "registered" in i.message
    ]

    assert bool(issues) is reported
