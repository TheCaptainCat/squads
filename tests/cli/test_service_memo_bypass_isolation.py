"""The invocation-scoped ``Service`` memo (``_cli/_common.py::get_service``) and the one
construction path deliberately different from it
(``get_service_bypassing_index_cross_check``, used by ``sq repair`` and as ``sq check``'s
fallback) must never be confused for one another. The hole runs both directions:

- a bypass-built (cross-check-skipping) instance memoized and later served to a plain
  caller would silently skip a fail-closed check;
- a plain instance short-circuiting the bypass path's own recovery would reinstate the
  very refusal the bypass path exists to clear.

Both are exercised directly against the two functions, with a stand-in Click root context
(the memo's anchor) held constant across calls to represent "one invocation" without a full
CLI dispatch — the anchor itself (``ctx.meta`` keyed off the Click root context, gated on the
read-scope marker) is exercised end-to-end elsewhere
(``tests/cli/test_show_json_single_index_load.py``).
"""

import pytest

import squads._cli._common as common
from squads._errors import SquadsError
from squads._services._service import Service

pytestmark = pytest.mark.anyio


class _FakeRootContext:
    """Minimal stand-in for a Click root ``Context``: a ``meta`` dict plus the
    ``call_on_close`` hook the real anchor uses — enough for ``get_service``/
    ``get_service_bypassing_index_cross_check`` to treat it as "one invocation" with an open
    read scope, with no real Click dispatch involved."""

    def __init__(self) -> None:
        self.meta: dict[str, object] = {common._READ_SCOPE_META_KEY: object()}

    def call_on_close(self, fn: object) -> None:  # pragma: no cover - not exercised here
        pass


@pytest.fixture
def one_invocation(monkeypatch):
    """Bind a single, stable fake root context for the duration of a test — everything
    ``get_service``/``get_service_bypassing_index_cross_check`` do within it shares that one
    anchor, exactly like both bridge crossings of one real CLI invocation do."""
    root = _FakeRootContext()
    monkeypatch.setattr(common, "_click_root_context", lambda: root)
    return root


async def test_bypass_fallback_is_never_served_to_a_later_plain_caller(
    project, one_invocation, monkeypatch
):
    """Direction one: the cross-check is failing for the whole invocation (as it genuinely is
    for ``sq repair``). The bypass path recovers with its own unvalidated fallback; a plain
    caller later in the same invocation must still see the refusal, never the bypass
    instance."""
    monkeypatch.setattr(
        common,
        "open_service",
        lambda *a, **kw: (_ for _ in ()).throw(SquadsError("simulated cross-check refusal")),
    )

    bypass_svc = common.get_service_bypassing_index_cross_check()
    assert isinstance(bypass_svc, Service)
    assert common._BYPASS_SERVICE_META_KEY in one_invocation.meta
    assert common._SERVICE_META_KEY not in one_invocation.meta, (
        "the bypass fallback must never be filed under the plain memo key"
    )

    with pytest.raises(SquadsError):
        common.get_service()


async def test_bypass_path_still_recovers_when_the_cross_check_fails(
    project, one_invocation, monkeypatch
):
    """Direction two, the mirror: memoization must not make the bypass path start
    propagating the refusal it exists to swallow — repair must still get a working
    ``Service`` back, not the plain caller's ``SquadsError`` reinstated."""
    monkeypatch.setattr(
        common,
        "open_service",
        lambda *a, **kw: (_ for _ in ()).throw(SquadsError("simulated cross-check refusal")),
    )

    svc = common.get_service_bypassing_index_cross_check()
    assert isinstance(svc, Service)

    # A second call in the same invocation reuses the memoized fallback rather than
    # rebuilding (and rather than raising).
    again = common.get_service_bypassing_index_cross_check()
    assert again is svc


async def test_bypass_path_reuses_an_already_successful_plain_memo(project, one_invocation):
    """When the cross-check is not actually failing, the bypass path's own first step —
    ``get_service()`` — succeeds and is what it returns: no separate, redundant,
    cross-check-skipping construction is built when the validated one already answers."""
    svc = common.get_service()
    assert common._SERVICE_META_KEY in one_invocation.meta

    bypass_svc = common.get_service_bypassing_index_cross_check()
    assert bypass_svc is svc
    assert common._BYPASS_SERVICE_META_KEY not in one_invocation.meta, (
        "no bypass-specific construction should ever happen when the plain path is healthy"
    )


async def test_plain_and_bypass_memos_never_share_a_slot(project, one_invocation, monkeypatch):
    """Structural isolation, directly: populate the bypass slot while the cross-check is
    failing, then let it recover and confirm a plain call builds and files its own answer
    under its own key rather than ever reading the bypass one filed a moment earlier."""
    real_open_service = common.open_service
    monkeypatch.setattr(
        common,
        "open_service",
        lambda *a, **kw: (_ for _ in ()).throw(SquadsError("simulated cross-check refusal")),
    )
    bypass_svc = common.get_service_bypassing_index_cross_check()
    assert common._BYPASS_SERVICE_META_KEY in one_invocation.meta

    # Now the cross-check recovers (a later call succeeds) — the plain path must build and
    # file its own answer, not reuse the bypass one filed above.
    monkeypatch.setattr(common, "open_service", real_open_service)
    plain_svc = common.get_service()
    assert plain_svc is not bypass_svc
    assert common._SERVICE_META_KEY in one_invocation.meta
