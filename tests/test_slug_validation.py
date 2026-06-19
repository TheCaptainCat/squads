"""BUG-000021: slug validation across sq mine, sq inbox, comment --as, and update surfaces.

Tests the ``resolve_slug_or_raise`` helper (service-level) and every CLI surface
that accepts a slug: sq mine, sq inbox, sq list --assignee, comment --as,
update --assignee, and update --author.
"""

import pytest

from squads._cli._common import resolve_slug_or_raise  # pyright: ignore[reportPrivateUsage]
from squads._errors import SquadsError
from squads._models._enums import ItemType

pytestmark = pytest.mark.anyio

# ----------------------------------------------------------------- service-level helper


async def test_resolve_slug_accepts_registered_agent(svc):
    slug = await resolve_slug_or_raise("manager", svc)
    assert slug == "manager"


async def test_resolve_slug_accepts_operator(svc):
    await svc.add_operator("Pierre Chat")
    slug = await resolve_slug_or_raise("op-pierre", svc)
    assert slug == "op-pierre"


async def test_resolve_slug_accepts_operator_sentinel(svc):
    # "operator" is the legacy anonymous sentinel; always accepted without roster lookup
    slug = await resolve_slug_or_raise("operator", svc)
    assert slug == "operator"


async def test_resolve_slug_raises_on_unknown_slug(svc):
    with pytest.raises(SquadsError, match="unknown slug"):
        await resolve_slug_or_raise("ghost", svc)


async def test_resolve_slug_error_names_valid_slugs(svc):
    await svc.add_operator("Pierre Chat")
    with pytest.raises(SquadsError) as exc_info:
        await resolve_slug_or_raise("nobody", svc)
    msg = str(exc_info.value)
    # message must list at least one registered participant
    assert "manager" in msg or "op-pierre" in msg


async def test_resolve_slug_normalises_at_prefix(svc):
    slug = await resolve_slug_or_raise("@manager", svc)
    assert slug == "manager"


# ----------------------------------------------------------------- sq mine


async def test_mine_requires_slug(invoke, project):
    r = await invoke(["mine"])
    assert r.exit_code != 0


async def test_mine_unknown_slug_exits_1_with_message(invoke, project):
    r = await invoke(["mine", "totally-unknown"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_mine_valid_agent_slug_works(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager", "--assignee", "manager"])
    r = await invoke(["mine", "manager"])
    assert r.exit_code == 0
    assert "TASK-000002" in r.output


async def test_mine_valid_operator_slug_works(invoke, project):
    await invoke(["operator", "add", "Pierre Chat"])
    await invoke(["create", "task", "T", "--author", "manager", "--assignee", "op-pierre"])
    r = await invoke(["mine", "op-pierre"])
    assert r.exit_code == 0
    assert "TASK-000003" in r.output


# ----------------------------------------------------------------- sq inbox


async def test_inbox_unknown_slug_exits_1_with_message(invoke, project):
    r = await invoke(["inbox", "totally-unknown"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_inbox_valid_slug_works(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "comment", "--as", "manager", "-m", "@manager please review"])
    r = await invoke(["inbox", "manager"])
    assert r.exit_code == 0
    assert "TASK-000002" in r.output


# ----------------------------------------------------------------- comment --as


async def test_comment_as_unknown_slug_exits_1(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "comment", "--as", "ghost", "-m", "hello"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_comment_as_operator_sentinel_works(invoke, project):
    """'operator' is the legacy sentinel — always valid, never roster-checked."""
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "comment", "--as", "operator", "-m", "noted"])
    assert r.exit_code == 0


async def test_comment_as_registered_agent_works(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "comment", "--as", "manager", "-m", "lgtm"])
    assert r.exit_code == 0


async def test_comment_as_operator_slug_works(invoke, project):
    await invoke(["operator", "add", "Pierre Chat"])
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "3", "comment", "--as", "op-pierre", "-m", "approved"])
    assert r.exit_code == 0


# ----------------------------------------------------------------- update --assignee / --author


async def test_update_assignee_unknown_slug_exits_1(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "update", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_update_author_unknown_slug_exits_1(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "update", "--author", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_update_assignee_valid_slug_works(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "update", "--assignee", "manager"])
    assert r.exit_code == 0


# ----------------------------------------------------------------- sq list --assignee


async def test_list_unknown_assignee_exits_1(invoke, project):
    r = await invoke(["list", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_list_valid_assignee_works(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager", "--assignee", "manager"])
    r = await invoke(["list", "--assignee", "manager"])
    assert r.exit_code == 0
    assert "TASK-000002" in r.output


async def test_list_operator_assignee_works(invoke, project):
    await invoke(["operator", "add", "Pierre Chat"])
    await invoke(["create", "task", "T", "--author", "manager", "--assignee", "op-pierre"])
    r = await invoke(["list", "--assignee", "op-pierre"])
    assert r.exit_code == 0
    assert "TASK-000003" in r.output


# ----------------------------------------------------------------- subtask --assignee


async def test_subtask_add_unknown_assignee_exits_1(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    r = await invoke(["task", "2", "add-subtask", "wire", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_subtask_update_unknown_assignee_exits_1(invoke, project):
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "2", "add-subtask", "wire"])
    r = await invoke(["task", "2", "subtask", "1", "update", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


async def test_subtask_update_valid_operator_assignee_works(invoke, project):
    await invoke(["operator", "add", "Pierre Chat"])
    await invoke(["create", "task", "T", "--author", "manager"])
    await invoke(["task", "3", "add-subtask", "wire"])
    r = await invoke(["task", "3", "subtask", "1", "update", "--assignee", "op-pierre"])
    assert r.exit_code == 0


# ----------------------------------------------------------------- create ItemType + operator


async def test_create_item_with_operator_as_author_still_validates(svc):
    """Service-level: operator slug is a valid author on work items."""
    await svc.add_operator("Pierre Chat")
    res = await svc.create(ItemType.TASK, "manual", author="op-pierre")
    assert res.item.author == "op-pierre"
