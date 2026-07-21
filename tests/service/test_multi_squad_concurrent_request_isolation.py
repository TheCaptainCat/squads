"""The concurrency-isolation capstone: a long-lived process serving N interleaved requests
across multiple squads must be semantically identical to N fresh single-shot processes.

Each "request" below binds its own `RequestContext` (client cwd, forged clock, actor, active
dir) inside its own asyncio task — the same seam the CLI edge's `main_callback` binds once per
invocation (see `squads._context`'s module docstring for the full data-vs-code triage rule).
Three properties are proven, each by a test scoped to exactly what it exercises:

- **ambient-context isolation, genuinely concurrent**: while one task's context is bound and
  held live, a second task running concurrently in the same task group never observes its
  clock/actor/dir — each asyncio task carries its own independent copy of the ambient context.
  This is the property a plain module-global regression would break (it would leak one task's
  bound context into the other, so a write meant for one squad would land in the other's store).
- **cross-squad data separation**: two different squads are two different index files on disk,
  so nothing one squad's request does is ever visible to the other's — this is a structural
  fact of separate storage, not a race being resolved, and the tests below name it as such.
- **the code-vs-data cache boundary, same squad**: a write committed by one request is visible
  to a concurrently-running *different* request for the *same* squad the moment the write
  returns — every request opens its own fresh `Service`/`IndexStore` and re-reads through the
  filelock, so there is no cross-request cache to serve a stale read.
"""

from datetime import UTC, datetime
from pathlib import Path

import anyio
import pytest

from squads import _actor as actor
from squads import _clock as clock
from squads._context import RequestContext, bind_context, get_context
from squads._services import _service as service

pytestmark = pytest.mark.anyio

_CLOCK_A = datetime(2020, 1, 1, tzinfo=UTC)
_CLOCK_B = datetime(2030, 6, 15, tzinfo=UTC)


async def _init_squad(root: Path) -> Path:
    result = await service.init(root=root, roles_spec="minimal", no_claude=True)
    return result.paths.squad_dir


async def test_ambient_context_never_bleeds_between_two_concurrent_squad_requests(
    tmp_path: Path,
) -> None:
    """The genuinely concurrent property: request A's context is bound and held live (parked
    on `b_checked`) while request B's task runs and samples the ambient context — a
    plain-module-global regression would make B observe A's dir/clock/actor (or vice versa),
    and A's own read-back after B unblocks it would then land in the wrong squad. A's write is
    sequenced strictly after B's check (not concurrent with it) — B's "squad B has nothing"
    assertion is cross-squad data separation (a structural fact of separate index files), not
    a race this test resolves; it's included so the story is complete, not as the isolation
    proof itself.
    """
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    squad_a = await _init_squad(root_a)
    squad_b = await _init_squad(root_b)

    a_bound = anyio.Event()
    b_checked = anyio.Event()
    created: dict[str, str] = {}

    async def request_for_a() -> None:
        bind_context(
            RequestContext(
                active_dir=str(squad_a),
                client_cwd=root_a,
                clock_override=_CLOCK_A,
                actor_override="python-dev",
                session_id="session-a",
            )
        )
        a_bound.set()
        # Hold the bound context live until B has sampled its own, concurrently, so a
        # cross-task bleed would actually have a window to happen in.
        await b_checked.wait()
        ctx = get_context()
        svc = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
        result = await svc.create("task", "Written by request A")
        created["item_id"] = result.item.id

    async def request_for_b() -> None:
        await a_bound.wait()
        bind_context(
            RequestContext(
                active_dir=str(squad_b),
                client_cwd=root_b,
                clock_override=_CLOCK_B,
                actor_override="qa",
                session_id="session-b",
            )
        )
        # Sampled while request A's context is bound concurrently in its own task — asyncio
        # tasks each hold an independent copy of the ambient context, so none of A's fields
        # (dir/clock/actor) are visible here. This is the genuine isolation assertion.
        ctx = get_context()
        assert ctx.active_dir == str(squad_b)
        assert ctx.client_cwd == root_b
        assert clock.now() == _CLOCK_B
        assert actor.current_actor() == "qa"

        # Squad B's own index has nothing from squad A — true by construction (a different
        # index file), not because a race was won; noted for completeness, not as the proof.
        svc = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
        items = await svc.list_items(item_type="task")
        assert items == []
        b_checked.set()

    async with anyio.create_task_group() as tg:
        tg.start_soon(request_for_b)
        tg.start_soon(request_for_a)

    assert "item_id" in created

    # The NEXT request for A: a fresh context, a fresh Service/IndexStore, re-reading through
    # the filelock — never the same `svc` object request_for_a used. Proves the committed
    # write is durable and visible without any cross-request data cache (serial, same squad;
    # the same property is proven under genuine concurrency in the test below).
    bind_context(
        RequestContext(active_dir=str(squad_a), client_cwd=root_a, session_id="session-a-2")
    )
    ctx = get_context()
    next_svc_a = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
    items_a = await next_svc_a.list_items(item_type="task")
    assert created["item_id"] in {i.id for i in items_a}

    # B's index still has nothing from A — again, structural (separate storage), not a race.
    bind_context(
        RequestContext(active_dir=str(squad_b), client_cwd=root_b, session_id="session-b-2")
    )
    ctx = get_context()
    next_svc_b = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
    items_b = await next_svc_b.list_items(item_type="task")
    assert items_b == []


async def test_a_same_squad_concurrent_reader_sees_the_write_the_moment_it_commits(
    tmp_path: Path,
) -> None:
    """The code-vs-data cache boundary, exercised where it actually matters: two requests
    against the SAME squad, running as concurrent tasks in one task group (not sequenced in
    the test body). The reader is unblocked the instant the writer's commit returns, then
    opens its own fresh `Service`/`IndexStore` — never the writer's own `svc` object — and
    must see the write. A cross-request data cache (exactly what the code-vs-data boundary
    forbids) would be the only way this could serve a stale (empty) read.
    """
    root = tmp_path / "squad"
    root.mkdir()
    squad_dir = await _init_squad(root)

    committed = anyio.Event()
    written: dict[str, str] = {}
    seen: dict[str, set[str]] = {}

    async def writer() -> None:
        bind_context(
            RequestContext(active_dir=str(squad_dir), client_cwd=root, session_id="writer")
        )
        ctx = get_context()
        svc = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
        result = await svc.create("task", "Committed by the writer")
        written["item_id"] = result.item.id
        committed.set()

    async def reader() -> None:
        await committed.wait()
        bind_context(
            RequestContext(active_dir=str(squad_dir), client_cwd=root, session_id="reader")
        )
        ctx = get_context()
        svc = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
        items = await svc.list_items(item_type="task")
        seen["ids"] = {i.id for i in items}

    async with anyio.create_task_group() as tg:
        tg.start_soon(writer)
        tg.start_soon(reader)

    assert seen["ids"] == {written["item_id"]}


async def test_four_interleaved_requests_across_two_squads_each_see_only_their_own_squad(
    tmp_path: Path,
) -> None:
    """A broader interleaving: two writers (one per squad) run concurrently, then two
    readers (one per squad) run concurrently — every reader sees exactly its own squad's
    write and nothing from the other (cross-squad separation again — a structural property
    of separate storage, exercised here across a wider fan-out)."""
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    root_a.mkdir()
    root_b.mkdir()
    squad_a = await _init_squad(root_a)
    squad_b = await _init_squad(root_b)

    written: dict[str, str] = {}

    async def writer(label: str, squad_dir: Path, root: Path) -> None:
        bind_context(
            RequestContext(active_dir=str(squad_dir), client_cwd=root, session_id=f"w-{label}")
        )
        ctx = get_context()
        svc = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
        result = await svc.create("task", f"Written by {label}")
        written[label] = result.item.id

    async with anyio.create_task_group() as tg:
        tg.start_soon(writer, "a", squad_a, root_a)
        tg.start_soon(writer, "b", squad_b, root_b)

    seen: dict[str, set[str]] = {}

    async def reader(label: str, squad_dir: Path, root: Path) -> None:
        bind_context(
            RequestContext(active_dir=str(squad_dir), client_cwd=root, session_id=f"r-{label}")
        )
        ctx = get_context()
        svc = service.open_service(ctx.active_dir, client_cwd=ctx.client_cwd)
        items = await svc.list_items(item_type="task")
        seen[label] = {i.id for i in items}

    async with anyio.create_task_group() as tg:
        tg.start_soon(reader, "a", squad_a, root_a)
        tg.start_soon(reader, "b", squad_b, root_b)

    assert seen["a"] == {written["a"]}
    assert seen["b"] == {written["b"]}
