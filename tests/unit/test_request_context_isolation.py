"""``squads._context``: the ``RequestContext`` primitive itself, and the isolation
guarantee it exists to provide — two logically-concurrent requests that each rebind
clock/actor/session must never observe each other's values.
"""

from datetime import UTC, datetime

import anyio
import anyio.lowlevel
import pytest

from squads import _actor as actor
from squads import _clock as clock
from squads._context import RequestContext, bind_context, get_context, rebind

pytestmark = pytest.mark.anyio


def test_get_context_returns_the_all_unset_default_when_nothing_was_bound() -> None:
    assert get_context() == RequestContext()


def test_bind_context_replaces_the_ambient_context_wholesale() -> None:
    bind_context(RequestContext(actor_override="qa"))
    assert get_context().actor_override == "qa"
    assert get_context().clock_override is None


def test_rebind_changes_only_the_named_field_and_returns_the_new_context() -> None:
    bind_context(RequestContext(actor_override="qa", session_id="sess-1"))
    new_ctx = rebind(actor_override="tech-lead")
    assert new_ctx.actor_override == "tech-lead"
    assert new_ctx.session_id == "sess-1"  # untouched
    assert get_context() == new_ctx


async def test_concurrent_contexts_do_not_observe_each_others_clock_actor_or_session() -> None:
    """Two sibling asyncio tasks, each a stand-in for a concurrent request, rebind the
    context to different values and must each read back only their own."""
    seen: dict[str, tuple[datetime, str, tuple[str | None, str | None]]] = {}

    async def _run(label: str, at: datetime, who: str, session: tuple[str, str]) -> None:
        clock.set_now(at)
        actor.set_actor(who)
        actor.seed_session(*session)
        await anyio.lowlevel.checkpoint()  # yield so the sibling task interleaves on this thread
        seen[label] = (clock.now(), actor.current_actor(), actor.current_session())

    async with anyio.create_task_group() as tg:
        tg.start_soon(_run, "a", datetime(2020, 1, 1, tzinfo=UTC), "python-dev", ("sess-a", "pa"))
        tg.start_soon(_run, "b", datetime(2021, 2, 2, tzinfo=UTC), "qa", ("sess-b", "pb"))

    assert seen["a"] == (datetime(2020, 1, 1, tzinfo=UTC), "python-dev", ("sess-a", "pa"))
    assert seen["b"] == (datetime(2021, 2, 2, tzinfo=UTC), "qa", ("sess-b", "pb"))
