"""The workflow index cross-check runs at most once per invocation — the root callback's
resolved spec is reused by ``open_service`` rather than re-parsed — and still refuses on every
command form, with nothing here cached stale across a rebound spec."""

from dataclasses import replace
from pathlib import Path

import pytest

from squads._cli import _common as common
from squads._context import bind_context, get_context
from squads._errors import SquadsError
from squads._models._index import SquadsDB
from squads._services._service import open_service

pytestmark = pytest.mark.anyio

# A benign override: adds a status, conflicts with no live item.
_BENIGN_OVERRIDE = '[statuses.Frobbed]\nrole = "pending"\n'

# A conflicting override: drops a badge code a live item still carries.
_CONFLICTING_OVERRIDE = (
    '[collections.priority]\nlabel = "Priority"\n'
    'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n'
)


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


def _count_index_parses(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Count every whole-index parse for the invocation, from either read path."""
    calls = [0]
    original = SquadsDB.model_validate_json.__func__

    def wrapped(cls: type[SquadsDB], *a: object, **kw: object) -> SquadsDB:
        calls[0] += 1
        return original(cls, *a, **kw)

    monkeypatch.setattr(SquadsDB, "model_validate_json", classmethod(wrapped))
    return calls


async def _seed_one_task(invoke, *, priority: str | None = None) -> str:
    """Create one task and sync, so a first-sync write burst never pollutes a parse count."""
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
    """With an override present, the cross-check runs exactly once plus the one real read."""
    task_id = await _seed_one_task(invoke)
    n = task_id.rsplit("-", 1)[-1]
    _write_override(project.squad_dir, _BENIGN_OVERRIDE)

    calls = _count_index_parses(monkeypatch)
    result = await invoke(args_fn(n))
    assert result.exit_code == 0, result.output
    assert calls[0] == 2, f"{label}: expected 2 parses with a workflow override, got {calls[0]}"


# --------------------------------------------------------------------------- the gate still refuses


@pytest.mark.parametrize(
    ("label", "args_fn"),
    [
        ("sq list", lambda n: ["list"]),
        ("sq <type> <n> show --json", lambda n: ["task", n, "show", "--json"]),
        ("sq sync", lambda n: ["sync"]),
    ],
)
async def test_gate_still_refuses_on_a_corpus_conflict(project, invoke, label, args_fn) -> None:
    """The cross-check gate exits 1 and names the offending item and code, per command form."""
    task_id = await _seed_one_task(invoke, priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    result = await invoke(args_fn(task_id.rsplit("-", 1)[-1]))
    assert result.exit_code == 1, f"{label}: expected the gate to refuse, got {result.output}"
    assert task_id in result.output, label
    assert "urgent" in result.output, label


async def test_check_still_degrades_gracefully_on_a_corpus_conflict(project, invoke) -> None:
    """`sq check` catches the SquadsError itself, reports it, and continues every other check."""
    await _seed_one_task(invoke, priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    result = await invoke(["check"])
    assert "workflow config invalid" in result.output
    assert "sq workflow lint" in result.output


async def test_repair_bypass_path_does_not_regain_the_refusal(project, invoke) -> None:
    """`sq repair` clears the cross-check refusal rather than reinstating it."""
    await _seed_one_task(invoke, priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    result = await invoke(["repair"])
    assert result.exit_code == 0, result.output
    assert "rebuilt index" in result.output


# --------------------------------------------------------------------------- keying


async def test_build_plain_service_always_uses_the_currently_bound_spec(
    project, monkeypatch
) -> None:
    """Two calls with the ambient spec rebound between them each use the current binding."""
    from squads._workflow import bundled_spec

    captured: list[object] = []

    def spy(dir_override, *, client_cwd=None, resolved_spec=None):
        captured.append(resolved_spec)
        return open_service(dir_override, client_cwd=client_cwd, resolved_spec=resolved_spec)

    monkeypatch.setattr(common, "open_service", spy)

    spec_a = bundled_spec()
    spec_b = spec_a.model_copy()
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
    """A direct ``open_service()`` call always resolves and cross-checks for itself, no
    matter what the ambient context holds."""
    from squads._workflow import bundled_spec

    result = await svc.create("task", "Urgent", author="manager", priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    prior = get_context()
    try:
        bind_context(replace(prior, active_spec=bundled_spec(), spec_error=None))
        with pytest.raises(SquadsError) as exc_info:
            open_service(str(project.squad_dir))
    finally:
        bind_context(prior)
    assert result.item.id in str(exc_info.value)


async def test_repeated_open_service_calls_on_one_directory_all_refuse(project, svc) -> None:
    """Every repeated ``open_service`` call against one directory validates independently."""
    result = await svc.create("task", "Urgent", author="manager", priority="urgent")
    _write_override(project.squad_dir, _CONFLICTING_OVERRIDE)

    for _ in range(3):
        with pytest.raises(SquadsError) as exc_info:
            open_service(str(project.squad_dir))
        assert result.item.id in str(exc_info.value)


async def test_resolved_spec_is_the_documented_opt_in_kwarg_default(project) -> None:
    """``open_service``'s ``resolved_spec`` parameter defaults to ``None``, an opt-in."""
    import inspect

    sig = inspect.signature(open_service)
    assert sig.parameters["resolved_spec"].default is None
