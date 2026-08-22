"""The workflow index cross-check (``validate_against_index_fail_closed``,
``_workflow/_loader.py``) used to run once per ``open_service`` call, and only when a workflow
override file is present — a second, fully redundant whole-index parse on top of the one the
CLI's root callback (``bind_active_spec``) already ran to bind the per-invocation spec every
other read surface consults. This closes that duplication: the root callback's already-resolved
(and, for an override, already cross-checked) spec is threaded straight into ``open_service``
(``resolved_spec``, ``_services/_service.py``) rather than re-loaded and re-checked a second
time, and a cached refusal (``RequestContext.spec_error``) is raised directly rather than
re-running the check just to reproduce the same ``SquadsError`` (``_build_plain_service``,
``_cli/_common.py``).

A parse count alone cannot tell "the check still runs, just once" apart from "the check was
quietly skipped" — a memo whose lookup succeeds where the check should have run is a fail-closed
gate silently turned off. So alongside the counts, this module drives: the gate still refusing
on every command form, individually; that nothing here is a cache that could go stale (no new
memo — each call reads the *currently* bound spec, and a direct, non-CLI-anchored call always
validates fully on its own); and that ``sq repair``'s cross-check-bypassing recovery path does
not regain the refusal it exists to clear.
"""

from dataclasses import replace
from pathlib import Path

import pytest

from squads._cli import _common as common
from squads._context import bind_context, get_context
from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._services._service import open_service

pytestmark = pytest.mark.anyio

# A benign override: adds a status, drops/conflicts with nothing a live item carries — the
# corpus stays valid, so every one of the four forms takes the success path all the way
# through.
_BENIGN_OVERRIDE = '[statuses.Frobbed]\nrole = "pending"\n'

# A conflicting override: shrinks the `priority` badge collection to drop the `urgent` code
# while a live item still carries it — the live-index cross-check's job is exactly to catch
# this (see tests/integration/test_workflow_override_service_integration.py).
_CONFLICTING_OVERRIDE = (
    '[collections.priority]\nlabel = "Priority"\n'
    'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n'
)


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def _count_index_parses(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """A live counter cell wired into ``SquadsDB.model_validate_json`` itself — every
    whole-index parse for the invocation, whether it comes from the async, scope-aware read
    path (``IndexStore._read_from_disk``) or the workflow loader's own synchronous
    cross-check read (``_load_index_sync``). Counts both, on purpose: the acceptance bar is
    the *total*, not either half of it.
    """
    calls = [0]
    original = SquadsDB.model_validate_json.__func__

    def wrapped(cls: type[SquadsDB], *a: object, **kw: object) -> SquadsDB:
        calls[0] += 1
        return original(cls, *a, **kw)

    monkeypatch.setattr(SquadsDB, "model_validate_json", classmethod(wrapped))
    return calls


async def _seed_one_task(invoke, *, priority: str | None = None) -> str:
    """One task item, then a stable ``sync`` — the fresh, already-synced corpus both the bug
    report and this task's own body drove their numbers against, so a first-ever ``sq sync``'s
    own (unrelated) burst of managed-file writes never pollutes the count being measured."""
    args = ["create", "task", "Probe task", "--author", "manager"]
    if priority is not None:
        args += ["--priority", priority]
    created = await invoke(args)
    assert created.exit_code == 0, created.output
    task_id = created.output.split()[1]
    synced = await invoke(["sync"])
    assert synced.exit_code == 0, synced.output
    return task_id


_FORMS: list[tuple[str, object]] = [
    ("sq list", lambda n: ["list"]),
    ("sq <type> <n> show --json", lambda n: ["task", n, "show", "--json"]),
    ("sq check", lambda n: ["check"]),
    ("sq sync", lambda n: ["sync"]),
]


# --------------------------------------------------------------------------- parse counts


@pytest.mark.parametrize(("label", "args_fn"), _FORMS)
async def test_no_override_parse_count_is_unchanged(
    project, invoke, monkeypatch, label, args_fn
) -> None:
    """The bundled-spec fast path never ran the cross-check at all — this must stay true."""
    task_id = await _seed_one_task(invoke)
    n = task_id.rsplit("-", 1)[-1]

    calls = _count_index_parses(monkeypatch)
    result = await invoke(args_fn(n))
    assert result.exit_code == 0, result.output
    assert calls[0] == 1, f"{label}: expected 1 parse with no override, got {calls[0]}"


@pytest.mark.parametrize(("label", "args_fn"), _FORMS)
async def test_workflow_override_parse_count_drops_from_three_to_two(
    project, invoke, monkeypatch, label, args_fn
) -> None:
    """The count this task exists to fix. Before: 3 (the root callback's own cross-check +
    open_service's own, fully redundant, second cross-check + the one real read). After: 2 —
    the cross-check now runs exactly once per invocation (root callback only; open_service
    reuses its result), plus the one real read every form still needs to do its actual work.

    2, not 1: the request-scoped read-snapshot design deliberately rules the cross-check out
    of the read scope, so it can never share the scope's one real read — a *fail-closed
    validation* memoized across reads is a strictly stronger (and disallowed) claim than
    memoizing a read result. One dedicated cross-check parse plus one real data read is the
    floor consistent with that ruling, not a partial fix.
    """
    task_id = await _seed_one_task(invoke)
    n = task_id.rsplit("-", 1)[-1]
    _write_override(project.squad_dir, _BENIGN_OVERRIDE)

    calls = _count_index_parses(monkeypatch)
    result = await invoke(args_fn(n))
    assert result.exit_code == 0, result.output
    assert calls[0] == 2, (
        f"{label}: expected 2 parses with a workflow override (was 3 before this fix), "
        f"got {calls[0]}"
    )


# --------------------------------------------------------------------------- the gate still
# refuses — proven per form, not once. A memo whose lookup succeeds where the check should
# have run is exactly the failure a parse count cannot show.


@pytest.mark.parametrize(
    ("label", "args_fn"),
    [
        ("sq list", lambda n: ["list"]),
        ("sq <type> <n> show --json", lambda n: ["task", n, "show", "--json"]),
        ("sq sync", lambda n: ["sync"]),
    ],
)
async def test_gate_still_refuses_on_a_corpus_conflict(project, invoke, label, args_fn) -> None:
    """The three hard-refusal forms: hitting the cross-check gate exits 1 and names the
    offending item and code, exactly as before this fix — only with one fewer redundant
    parse behind it."""
    task_id = await _seed_one_task(invoke, priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    result = await invoke(args_fn(task_id.rsplit("-", 1)[-1]))
    assert result.exit_code == 1, f"{label}: expected the gate to refuse, got {result.output}"
    assert task_id in result.output, label
    assert "urgent" in result.output, label


async def test_check_still_degrades_gracefully_on_a_corpus_conflict(project, invoke) -> None:
    """`sq check` is the one form that does not hard-refuse — it catches the SquadsError
    itself and degrades, reporting a CheckIssue while continuing every other check. That
    shape is unchanged by this fix; only the parse count behind it is."""
    await _seed_one_task(invoke, priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    result = await invoke(["check"])
    assert "workflow config invalid" in result.output
    assert "sq workflow lint" in result.output


async def test_repair_bypass_path_does_not_regain_the_refusal(project, invoke) -> None:
    """`sq repair`'s entire job is reconciling a corpus a broken/incompatible spec has
    stranded — it must keep clearing the exact refusal above, not reinstate it. This is the
    opposite failure from the gate silently turning off, and just as real."""
    await _seed_one_task(invoke, priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert "rebuilt index" in result.output


# --------------------------------------------------------------------------- keying: nothing
# here is a cache that can go stale. There is no new memo dict at all — ``_build_plain_service``
# only ever reads the *currently* bound ``RequestContext``, and a direct (non-CLI-anchored)
# ``open_service`` call always resolves and cross-checks fully on its own.


async def test_build_plain_service_always_uses_the_currently_bound_spec(
    project, monkeypatch
) -> None:
    """Two calls in one process, with the ambient spec rebound to a different object in
    between, must each pass through the *current* binding — proving there is nothing here a
    stale earlier resolution could leak through, unlike a memo keyed too loosely on
    ``squad_dir`` alone would risk."""
    from squads._workflow import bundled_spec

    captured: list[object] = []
    real_open_service = common.open_service

    def spy(dir_override, *, client_cwd=None, resolved_spec=None):
        captured.append(resolved_spec)
        return real_open_service(dir_override, client_cwd=client_cwd, resolved_spec=resolved_spec)

    monkeypatch.setattr(common, "open_service", spy)

    spec_a = bundled_spec()
    spec_b = spec_a.model_copy()  # a distinct object, deliberately, even if content-equal
    assert spec_a is not spec_b

    prior = get_context()
    try:
        bind_context(replace(prior, active_spec=spec_a, spec_error=None))
        common._build_plain_service()
        bind_context(replace(prior, active_spec=spec_b, spec_error=None))
        common._build_plain_service()
    finally:
        bind_context(prior)

    assert captured == [spec_a, spec_b]


async def test_open_service_direct_call_ignores_an_unrelated_ambient_spec(
    project, svc, monkeypatch
) -> None:
    """A caller that does not go through ``_build_plain_service`` — a direct ``open_service()``
    call, exactly what a test or a second ``IndexStore`` on the same directory makes (``sq
    ui`` is not this: it still calls ``get_service()``, which reaches ``_build_plain_service``
    the same as every other CLI command) — must never be handed a shortcut it did not ask
    for: it always resolves and cross-checks for itself, no matter what the ambient
    ``RequestContext`` happens to hold."""
    from squads._workflow import bundled_spec

    result = await svc.create("task", "Urgent", author="manager", priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    # The ambient context claims a clean, unrelated (bundled) spec with no error — a plain
    # `_build_plain_service()` call would trust that and skip its own check. A direct call
    # must not: it takes no `resolved_spec` and re-derives everything itself.
    prior = get_context()
    try:
        bind_context(replace(prior, active_spec=bundled_spec(), spec_error=None))
        with pytest.raises(SquadsError) as exc_info:
            open_service(str(project.squad_dir))
    finally:
        bind_context(prior)
    assert result.item.id in str(exc_info.value)


async def test_repeated_open_service_calls_on_one_directory_all_refuse(project, svc) -> None:
    """Simulates a second (or third) ``IndexStore``/``Service`` construction against the same
    squad directory within one process — legitimate per the read-scope design (one can be
    mid-rebuild).
    Each construction validates independently: none of them is exempted because an earlier
    one already ran, and none of them wrongly succeeds because a later one will."""
    result = await svc.create("task", "Urgent", author="manager", priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    for _ in range(3):
        with pytest.raises(SquadsError) as exc_info:
            open_service(str(project.squad_dir))
        assert result.item.id in str(exc_info.value)


async def test_resolved_spec_is_the_documented_opt_in_kwarg_default(project) -> None:
    """``open_service``'s new ``resolved_spec`` parameter defaults to ``None`` — every
    existing caller that reaches ``open_service`` directly rather than through
    ``get_service()`` (a test calling it itself, most commonly) is unaffected unless it
    explicitly opts in. ``sq ui`` and the bypass fallback's own first step both go through
    ``get_service()`` and so already supply ``resolved_spec``; only that fallback's steps 2/3
    skip ``open_service`` entirely."""
    import inspect

    sig = inspect.signature(open_service)
    assert sig.parameters["resolved_spec"].default is None
