"""BUG-000021: slug validation across sq mine, sq inbox, comment --as, and update surfaces.

Tests the ``resolve_slug_or_raise`` helper (service-level) and every CLI surface
that accepts a slug: sq mine, sq inbox, sq list --assignee, comment --as,
update --assignee, and update --author.
"""

import pytest

from squads._cli import app
from squads._cli._common import resolve_slug_or_raise  # pyright: ignore[reportPrivateUsage]
from squads._errors import SquadsError
from squads._models._enums import ItemType

# ----------------------------------------------------------------- service-level helper


def test_resolve_slug_accepts_registered_agent(svc):
    slug = resolve_slug_or_raise("manager", svc)
    assert slug == "manager"


def test_resolve_slug_accepts_operator(svc):
    svc.add_operator("Pierre Chat")
    slug = resolve_slug_or_raise("op-pierre", svc)
    assert slug == "op-pierre"


def test_resolve_slug_accepts_operator_sentinel(svc):
    # "operator" is the legacy anonymous sentinel; always accepted without roster lookup
    slug = resolve_slug_or_raise("operator", svc)
    assert slug == "operator"


def test_resolve_slug_raises_on_unknown_slug(svc):
    with pytest.raises(SquadsError, match="unknown slug"):
        resolve_slug_or_raise("ghost", svc)


def test_resolve_slug_error_names_valid_slugs(svc):
    svc.add_operator("Pierre Chat")
    with pytest.raises(SquadsError) as exc_info:
        resolve_slug_or_raise("nobody", svc)
    msg = str(exc_info.value)
    # message must list at least one registered participant
    assert "manager" in msg or "op-pierre" in msg


def test_resolve_slug_normalises_at_prefix(svc):
    slug = resolve_slug_or_raise("@manager", svc)
    assert slug == "manager"


# ----------------------------------------------------------------- sq mine


def test_mine_requires_slug(runner, project):
    r = runner.invoke(app, ["mine"])
    assert r.exit_code != 0


def test_mine_unknown_slug_exits_1_with_message(runner, project):
    r = runner.invoke(app, ["mine", "totally-unknown"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_mine_valid_agent_slug_works(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--assignee", "manager"])
    r = runner.invoke(app, ["mine", "manager"])
    assert r.exit_code == 0
    assert "TASK-000002" in r.output


def test_mine_valid_operator_slug_works(runner, project):
    runner.invoke(app, ["operator", "add", "Pierre Chat"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--assignee", "op-pierre"])
    r = runner.invoke(app, ["mine", "op-pierre"])
    assert r.exit_code == 0
    assert "TASK-000003" in r.output


# ----------------------------------------------------------------- sq inbox


def test_inbox_unknown_slug_exits_1_with_message(runner, project):
    r = runner.invoke(app, ["inbox", "totally-unknown"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_inbox_valid_slug_works(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", "@manager please review"])
    r = runner.invoke(app, ["inbox", "manager"])
    assert r.exit_code == 0
    assert "TASK-000002" in r.output


# ----------------------------------------------------------------- comment --as


def test_comment_as_unknown_slug_exits_1(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "comment", "--as", "ghost", "-m", "hello"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_comment_as_operator_sentinel_works(runner, project):
    """'operator' is the legacy sentinel — always valid, never roster-checked."""
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "comment", "--as", "operator", "-m", "noted"])
    assert r.exit_code == 0


def test_comment_as_registered_agent_works(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "comment", "--as", "manager", "-m", "lgtm"])
    assert r.exit_code == 0


def test_comment_as_operator_slug_works(runner, project):
    runner.invoke(app, ["operator", "add", "Pierre Chat"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "3", "comment", "--as", "op-pierre", "-m", "approved"])
    assert r.exit_code == 0


# ----------------------------------------------------------------- update --assignee / --author


def test_update_assignee_unknown_slug_exits_1(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "update", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_update_author_unknown_slug_exits_1(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "update", "--author", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_update_assignee_valid_slug_works(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "update", "--assignee", "manager"])
    assert r.exit_code == 0


# ----------------------------------------------------------------- sq list --assignee


def test_list_unknown_assignee_exits_1(runner, project):
    r = runner.invoke(app, ["list", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_list_valid_assignee_works(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--assignee", "manager"])
    r = runner.invoke(app, ["list", "--assignee", "manager"])
    assert r.exit_code == 0
    assert "TASK-000002" in r.output


def test_list_operator_assignee_works(runner, project):
    runner.invoke(app, ["operator", "add", "Pierre Chat"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager", "--assignee", "op-pierre"])
    r = runner.invoke(app, ["list", "--assignee", "op-pierre"])
    assert r.exit_code == 0
    assert "TASK-000003" in r.output


# ----------------------------------------------------------------- subtask --assignee


def test_subtask_add_unknown_assignee_exits_1(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    r = runner.invoke(app, ["task", "2", "add-subtask", "wire", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_subtask_update_unknown_assignee_exits_1(runner, project):
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "2", "add-subtask", "wire"])
    r = runner.invoke(app, ["task", "2", "subtask", "1", "update", "--assignee", "ghost"])
    assert r.exit_code == 1
    assert "unknown slug" in r.output


def test_subtask_update_valid_operator_assignee_works(runner, project):
    runner.invoke(app, ["operator", "add", "Pierre Chat"])
    runner.invoke(app, ["create", "task", "T", "--author", "manager"])
    runner.invoke(app, ["task", "3", "add-subtask", "wire"])
    r = runner.invoke(app, ["task", "3", "subtask", "1", "update", "--assignee", "op-pierre"])
    assert r.exit_code == 0


# ----------------------------------------------------------------- create ItemType + operator


def test_create_item_with_operator_as_author_still_validates(svc):
    """Service-level: operator slug is a valid author on work items."""
    svc.add_operator("Pierre Chat")
    res = svc.create(ItemType.TASK, "manual", author="op-pierre")
    assert res.item.author == "op-pierre"
