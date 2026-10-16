"""``sq check`` reports each role and operator, live or retired, whose slug is outside its
grammar or shared inside the author namespace, one error per entry with the replacing commands.
Creation can no longer produce such an entry, so the tests build them with the creation check
switched off, the way a hand-edited file or a merge would."""

import re

import pytest

from squads._errors import SquadsError
from squads._index._resolver import item_file
from squads._models._extras import ExtraKey as X
from squads._services import _base

pytestmark = pytest.mark.anyio

MARK = "remedy:"


@pytest.fixture
def unchecked_creation(monkeypatch):
    monkeypatch.setattr(_base, "_check_roster_slug", lambda *args, **kwargs: None)


async def _entry(svc, kind: str, slug: str, name: str = "Some Name"):
    return (
        await svc.create(
            kind, name, slug=slug, author="manager", extra={X.SLUG: slug, X.FULL_NAME: name}
        )
    ).item


async def _hand_edited(svc, item, slug: str, *, keep_stored_slug: bool = True):
    """Edit an entry's file the way a merge or an older release leaves it, then rebuild the index
    from the files; with ``keep_stored_slug`` false the entry has no ``extra.slug``."""
    path = item_file(svc.paths, item)
    text = path.read_text(encoding="utf-8")
    text = re.sub(rf"^(\s*)slug: {re.escape(item.slug)}$", rf"\1slug: {slug}", text, flags=re.M)
    if not keep_stored_slug:
        text = re.sub(r"^  slug: .*\n", "", text, count=1, flags=re.M)
    path.write_text(text, encoding="utf-8")
    path.rename(path.with_name(path.name.replace(f"-{item.slug}.md", f"-{slug}.md")))
    await svc.repair()
    return await svc.get(item.id)


async def _reports(svc) -> dict[str, str]:
    return {i.item: i.message for i in await svc.check() if MARK in i.message}


#: (kind, slug, expected fragment of the one report)
BREACHES = [
    pytest.param(
        "operator", "squads", "operator slug 'squads' does not start with 'op-'", id="sys"
    ),
    pytest.param("operator", "operator", "does not start with 'op-'", id="anonymous"),
    pytest.param("operator", "Bad Slug", "does not start with 'op-'", id="space"),
    pytest.param("operator", "OP-UP", "does not start with 'op-'", id="capitals"),
    pytest.param(
        "operator", "op-", "is not 'op-' followed by lowercase letters, digits and hyphens", id="e"
    ),
    pytest.param("role", "op-dev", "role slug 'op-dev' is reserved for operators", id="op-role"),
    pytest.param("role", "squads", "role slug 'squads' is reserved for system", id="sys-role"),
    pytest.param("role", "Bad Slug", "is not lowercase letters, digits and hyphens", id="bad-role"),
]


@pytest.mark.parametrize(("kind", "slug", "fragment"), BREACHES)
async def test_an_entry_outside_its_grammar_is_reported_once_with_its_remedy(
    svc, unchecked_creation, kind, slug, fragment
) -> None:
    item = await _entry(svc, kind, slug)

    reports = await _reports(svc)

    assert list(reports) == [item.id]
    assert fragment in reports[item.id]
    assert f"sq {kind} {item.id} rm --purge" in reports[item.id]
    assert "sq operator add" in reports[item.id] or "sq role activate" in reports[item.id]


async def test_a_retired_breaching_operator_is_reported(svc, unchecked_creation) -> None:
    item = await _entry(svc, "operator", "qa")
    await svc.set_roster_status(item.id, "Archived")

    assert list(await _reports(svc)) == [item.id]


async def test_an_operator_holding_a_live_roles_slug_names_the_role_and_the_role_names_it(
    svc, unchecked_creation
) -> None:
    op = await _entry(svc, "operator", "qa", "Quentin Adams")
    role = await svc.activate_role("qa")

    reports = await _reports(svc)

    assert set(reports) == {op.id, role.id}
    assert (
        f"operator slug 'qa' does not start with 'op-'; it is also held by {role.id}"
        in (reports[op.id])
    )
    assert f"role slug 'qa' is not unique; it is also held by {op.id}" in reports[role.id]
    assert 'sq operator add "Quentin Adams"' in reports[op.id]


async def test_two_operators_sharing_a_compliant_slug_are_both_reported(
    svc, unchecked_creation
) -> None:
    first = await _entry(svc, "operator", "op-ann", "Ann One")
    second = await _hand_edited(svc, await _entry(svc, "operator", "op-ann2", "Ann Two"), "op-ann")

    reports = await _reports(svc)

    assert set(reports) == {first.id, second.id}
    assert (
        f"operator slug 'op-ann' is not unique; it is also held by {second.id}"
        in (reports[first.id])
    )
    assert f"it is also held by {first.id}" in reports[second.id]


async def test_a_skill_holding_the_system_slug_is_not_reported(svc) -> None:
    await svc.add_skill("squads")

    assert await _reports(svc) == {}


async def test_a_compliant_roster_reports_nothing(svc) -> None:
    await svc.add_operator("Anna Lee")
    await svc.add_dev("python")
    await svc.add_skill("Pairing")

    assert await _reports(svc) == {}


async def test_the_report_gates_no_write(svc, unchecked_creation) -> None:
    await _entry(svc, "operator", "squads")

    task = (await svc.create("task", "Unrelated", author="manager")).item
    updated = await svc.update(task.id, title="Still unrelated")

    assert updated.title == "Still unrelated"
    assert (await svc.add_operator("Anna Lee")).slug == "op-anna"


# --------------------------------------------------------------------------- legacy shapes


async def test_an_entry_an_older_release_wrote_without_a_stored_slug_is_checked_by_its_own_slug(
    svc,
) -> None:
    first = await svc.add_operator("Ann Lee")
    legacy = await svc.add_operator("Ann Two", slug="op-ann2")
    legacy = await _hand_edited(svc, legacy, "op-ann", keep_stored_slug=False)
    assert "slug" not in legacy.extra

    reports = await _reports(svc)

    assert set(reports) == {first.id, legacy.id}
    assert "is not unique" in reports[legacy.id]


async def test_an_older_entry_with_an_out_of_grammar_file_slug_is_reported(svc) -> None:
    legacy = await svc.add_operator("Ann Two", slug="op-ann2")
    legacy = await _hand_edited(svc, legacy, "ann-two", keep_stored_slug=False)

    assert list(await _reports(svc)) == [legacy.id]


async def test_an_older_entry_is_found_by_its_slug_and_blocks_a_second_operator_add(svc) -> None:
    legacy = await svc.add_operator("Ann Two", slug="op-ann2")
    legacy = await _hand_edited(svc, legacy, "op-ann", keep_stored_slug=False)

    assert (await svc.roster_item("operator", "op-ann")).id == legacy.id
    with pytest.raises(SquadsError, match="already exists"):
        await svc.add_operator("Ann Lee")


# --------------------------------------------------------------------------- remedies


async def test_a_shared_slug_remedy_carries_a_slug_for_the_re_add(svc, unchecked_creation) -> None:
    first = await _entry(svc, "operator", "op-ann", "Ann One")
    await _hand_edited(svc, await _entry(svc, "operator", "op-ann2", "Ann Two"), "op-ann")

    assert 'sq operator add "Ann One" --slug <compliant slug>' in (await _reports(svc))[first.id]


async def test_a_role_that_breaks_no_rule_is_pointed_at_the_operator_to_replace(
    svc, unchecked_creation
) -> None:
    op = await _entry(svc, "operator", "qa", "Quentin Adams")
    role = await svc.activate_role("qa")

    reports = await _reports(svc)

    assert f"remedy: replace {op.id}, which break a rule of their own" in reports[role.id]
    assert "rename the project role file" not in reports[role.id]
    assert "rename the project role file" not in reports[op.id]


async def test_a_retired_operator_is_retired_again_after_the_re_add(
    svc, unchecked_creation
) -> None:
    item = await _entry(svc, "operator", "qa")
    await svc.set_roster_status(item.id, "Archived")
    live = await _entry(svc, "operator", "squads")

    reports = await _reports(svc)

    assert reports[item.id].endswith("then sq operator <compliant slug> status Archived")
    assert "status" not in reports[live.id].split("remedy:")[1]


# --------------------------------------------------------------------------- group verbs


@pytest.mark.parametrize(
    ("kind", "slug"),
    [("role", "list"), ("role", "catalog"), ("role", "activate"), ("skill", "add")],
)
async def test_a_role_or_skill_holding_a_group_verb_is_reported_with_a_remedy(
    svc, unchecked_creation, kind, slug
) -> None:
    item = await _entry(svc, kind, slug)

    reports = await _reports(svc)

    assert list(reports) == [item.id]
    assert f"{kind} slug '{slug}' is a verb of `sq {kind}`" in reports[item.id]
    assert f"sq {kind} {item.id} rm --purge" in reports[item.id]


async def test_a_role_slug_that_is_a_skill_verb_and_a_skill_slug_that_is_a_role_verb_pass(
    svc, unchecked_creation
) -> None:
    await _entry(svc, "role", "add")
    await _entry(svc, "skill", "list")

    assert await _reports(svc) == {}
