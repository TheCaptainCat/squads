"""Every slug-accepting CLI surface rejects an unknown slug with an actionable message and
accepts a registered agent/operator (including the @-prefixed sentinel). One thin test per
surface — deliberately repeated per tests/CONVENTIONS.md's dedup discipline, since each
surface is an independent place the wiring to resolve_slug_or_raise could regress
independently. The validator itself is proven once at
tests/service/test_slug_resolution.py.
"""

import pytest

pytestmark = pytest.mark.anyio


class TestMine:
    async def test_requires_a_slug(self, invoke, project) -> None:
        r = await invoke(["mine"])
        assert r.exit_code != 0

    async def test_unknown_slug_exits_1(self, invoke, project) -> None:
        r = await invoke(["mine", "totally-unknown"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_a_valid_agent_slug_works(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager", "--assignee", "manager"])
        r = await invoke(["mine", "manager"])
        assert r.exit_code == 0
        assert "TASK-2" in r.output

    async def test_a_valid_operator_slug_works(self, invoke, project) -> None:
        await invoke(["operator", "add", "Pierre Chat"])
        await invoke(["create", "task", "T", "--author", "manager", "--assignee", "op-pierre"])
        r = await invoke(["mine", "op-pierre"])
        assert r.exit_code == 0
        assert "TASK-3" in r.output


class TestInbox:
    async def test_unknown_slug_exits_1(self, invoke, project) -> None:
        r = await invoke(["inbox", "totally-unknown"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_a_valid_slug_works(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        await invoke(["task", "2", "comment", "--as", "manager", "-m", "@manager please review"])
        r = await invoke(["inbox", "manager"])
        assert r.exit_code == 0
        assert "TASK-2" in r.output

    async def test_a_valid_slug_with_no_mentions_at_all_prints_a_clean_nothing_message(
        self, invoke, project
    ) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["inbox", "manager"])
        assert r.exit_code == 0
        assert "nothing for @manager" in r.output


class TestCommentAs:
    async def test_unknown_slug_exits_1(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "comment", "--as", "ghost", "-m", "hello"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_the_operator_sentinel_always_works(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "comment", "--as", "operator", "-m", "noted"])
        assert r.exit_code == 0

    async def test_a_registered_agent_slug_works(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "comment", "--as", "manager", "-m", "lgtm"])
        assert r.exit_code == 0

    async def test_a_registered_operator_slug_works(self, invoke, project) -> None:
        await invoke(["operator", "add", "Pierre Chat"])
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "3", "comment", "--as", "op-pierre", "-m", "approved"])
        assert r.exit_code == 0


class TestUpdateAssigneeAndAuthor:
    async def test_unknown_assignee_exits_1(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "update", "--assignee", "ghost"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_unknown_author_exits_1(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "update", "--author", "ghost"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_a_valid_assignee_works(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "update", "--assignee", "manager"])
        assert r.exit_code == 0


class TestListAssignee:
    async def test_unknown_assignee_exits_1(self, invoke, project) -> None:
        r = await invoke(["list", "--assignee", "ghost"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_a_valid_agent_assignee_works(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager", "--assignee", "manager"])
        r = await invoke(["list", "--assignee", "manager"])
        assert r.exit_code == 0
        assert "TASK-2" in r.output

    async def test_a_valid_operator_assignee_works(self, invoke, project) -> None:
        await invoke(["operator", "add", "Pierre Chat"])
        await invoke(["create", "task", "T", "--author", "manager", "--assignee", "op-pierre"])
        r = await invoke(["list", "--assignee", "op-pierre"])
        assert r.exit_code == 0
        assert "TASK-3" in r.output


class TestSubtaskAssignee:
    async def test_add_subtask_unknown_assignee_exits_1(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        r = await invoke(["task", "2", "add-subtask", "wire", "--assignee", "ghost"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_update_subtask_unknown_assignee_exits_1(self, invoke, project) -> None:
        await invoke(["create", "task", "T", "--author", "manager"])
        await invoke(["task", "2", "add-subtask", "wire"])
        r = await invoke(["task", "2", "subtask", "1", "update", "--assignee", "ghost"])
        assert r.exit_code == 1
        assert "unknown slug" in r.output

    async def test_update_subtask_a_valid_operator_assignee_works(self, invoke, project) -> None:
        await invoke(["operator", "add", "Pierre Chat"])
        await invoke(["create", "task", "T", "--author", "manager"])
        await invoke(["task", "3", "add-subtask", "wire"])
        r = await invoke(["task", "3", "subtask", "1", "update", "--assignee", "op-pierre"])
        assert r.exit_code == 0
