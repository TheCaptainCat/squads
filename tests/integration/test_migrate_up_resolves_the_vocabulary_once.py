"""``run_pending_migrations`` resolves the spec and playbook once and hands the same context to
every runner: a chain of runners shares one context, and none of them loads or fetches a spec
or a playbook of its own.
"""

import dataclasses
import shutil
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from _helpers import catalog_of, make_service
from squads import __version__
from squads._interactions._playbook import get_playbook_spec
from squads._migrations._context import MigrationContext
from squads._migrations._registry import MIGRATIONS
from squads._models._config import SquadsConfig
from squads._paths import SquadPaths
from squads._services import _maintenance
from squads._spec_documents import resolve_playbook
from squads._workflow import bundled_spec, load_workflow_spec

pytestmark = pytest.mark.anyio

_CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "corpus"
_RESOLVERS = ("load_workflow_spec", "load_playbook", "bundled_spec", "get_playbook_spec")


def _paths_at(root: Path) -> SquadPaths:
    with (root / ".squads.toml").open("rb") as fh:
        cfg = SquadsConfig.from_toml_dict(tomllib.load(fh))
    return SquadPaths(root=root, squad_dir=root / cfg.squad_dir, config=cfg)


def _count_resolutions(monkeypatch: pytest.MonkeyPatch, tally: list[str], live: list[bool]) -> None:
    """Replace every module-level binding of a resolver with a wrapper that records a call made
    while a runner is executing."""
    for module in list(sys.modules.values()):
        if not getattr(module, "__name__", "").startswith("squads"):
            continue
        for name in _RESOLVERS:
            original = getattr(module, name, None)
            if callable(original):
                monkeypatch.setattr(module, name, _recording(original, name, tally, live))


def _recording(
    fn: Callable[..., Any], name: str, tally: list[str], live: list[bool]
) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if live[0]:
            tally.append(name)
        return fn(*args, **kwargs)

    return wrapper


async def test_a_chain_of_runners_shares_one_context_and_resolves_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time
) -> None:
    root = tmp_path / "v0_8"
    shutil.copytree(_CORPUS_DIR / "v0_8", root)
    paths = _paths_at(root)
    overrides = paths.squad_dir / ".overrides"
    overrides.mkdir()
    header = f"# squads:override-base:{__version__}\n"
    (overrides / "workflow.toml").write_text(
        header + '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n',
        encoding="utf-8",
    )
    (overrides / "playbook.toml").write_text(
        header + '[types.incident]\noverview = "An incident."\n'
        'lifecycle = "Draft -> Active -> Archived"\n'
        'commands = ["sq create incident"]\n'
        'roles = [{ slug = "qa", authors = true }]\n',
        encoding="utf-8",
    )
    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    svc = make_service(
        paths,
        spec=spec,
        playbook=resolve_playbook(spec, paths.squad_dir, catalog_of(paths.squad_dir)),
    )
    assert svc.spec is not bundled_spec()
    assert svc.playbook is not get_playbook_spec()
    received: list[MigrationContext] = []
    tally: list[str] = []
    live = [False]

    def observed(run: Callable[[MigrationContext], Any]) -> Callable[[MigrationContext], Any]:
        async def wrapper(ctx: MigrationContext) -> Any:
            received.append(ctx)
            live[0] = True
            try:
                return await run(ctx)
            finally:
                live[0] = False

        return wrapper

    monkeypatch.setattr(
        _maintenance,
        "MIGRATIONS",
        [dataclasses.replace(m, run=observed(m.run)) for m in MIGRATIONS],
    )
    _count_resolutions(monkeypatch, tally, live)

    run = await svc.run_pending_migrations()

    assert len(run.applied) >= 3, "the chain should span several runners"
    assert len(received) == len(run.applied)
    assert all(ctx is received[0] for ctx in received)
    assert received[0].spec is svc.spec
    assert received[0].playbook is svc.playbook
    assert tally == []
