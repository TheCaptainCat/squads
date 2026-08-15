"""The ten bundled type aliases (``e f t b d r g feat dec rev``) are live root commands in
every squad because the import-time registration loop binds them unconditionally from the
bundled spec. That table must never out-rank the active spec's own declarations, in either
direction:

- a declared type (or alias) *named* after a bundled alias is refused at load, because the
  static table would otherwise silently serve it from the bundled owner's command tree —
  ``sq create feat "Collide"`` created a ``feature``;
- a bundled alias the active spec no longer declares stops dispatching, with a refusal that
  names the alias the owner declares now, instead of exiting 0 as though nothing changed.

Lint *messages* are asserted through ``lint_workflow_spec`` rather than the CLI's Rich table,
which hard-wraps them mid-phrase; the CLI's own contribution here is the exit code.
"""

import re
from pathlib import Path

import pytest

from squads import __version__
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow._loader import lint_workflow_spec
from squads._workflow._models import RESERVED_CLI_ALIASES

pytestmark = pytest.mark.anyio

_BUNDLED_ALIASES = [alias for alias, _owner in RESERVED_CLI_ALIASES]

_RENAMED_ALIASES_OVERRIDE = """\
[items.epic]
aliases = ["ep"]

[items.feature]
aliases = ["ft"]

[items.task]
aliases = ["tk"]

[items.bug]
aliases = ["bg"]

[items.decision]
aliases = ["adr"]

[items.review]
aliases = ["rv"]

[items.guide]
aliases = ["gd"]
"""


def _write_override(squad_dir: Path, body: str) -> None:
    """Write a *stamped* override — an override that shadows a bundled key owes provenance,
    and an unstamped one would add a second, unrelated lint error to every assertion here."""
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)


def _errors(squad_dir: Path) -> list[str]:
    return [
        message for level, _loc, message, _hint in lint_workflow_spec(squad_dir) if level == "error"
    ]


def _feature_num(create_output: str) -> str:
    m = re.search(r"FEAT-(\d+)", create_output)
    assert m is not None, f"could not find a FEAT-N id in:\n{create_output}"
    return m.group(1)


# ─── direction 1: a declared name colliding with a bundled alias ──────────────


@pytest.mark.parametrize(("alias", "owner"), RESERVED_CLI_ALIASES)
async def test_a_type_named_after_any_bundled_alias_is_refused_at_load(
    project, invoke, alias: str, owner: str
) -> None:
    _write_override(
        project.squad_dir,
        f'[items.{alias}]\nprefix = "X{alias.upper()}"\n'
        f'folder = "x-{alias}"\nlifecycle = "work"\norder = 75\n',
    )
    errors = _errors(project.squad_dir)
    assert any(f"item {alias!r}: shadows the built-in `sq {alias}` alias" in m for m in errors), (
        errors
    )
    assert any(owner in m for m in errors), errors

    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 1, linted.output


async def test_the_declared_type_never_silently_creates_the_bundled_one(project, invoke) -> None:
    """The symptom the refusal replaces: `sq create feat` used to make a FEAT-n typed
    `feature`, with only a lane advisory naming the wrong type."""
    _write_override(
        project.squad_dir,
        '[items.feat]\nprefix = "FEAT2"\nfolder = "feats"\nlifecycle = "work"\norder = 75\n',
    )
    created = await invoke(["create", "feat", "Collide", "--author", "manager"])
    assert created.exit_code != 0
    assert "FEAT-" not in created.output


async def test_an_alias_claimed_by_another_type_is_refused(project, invoke) -> None:
    """The owner *releases* the alias and another type claims it — so the plain duplicate-alias
    check finds nothing, and only the static-table collision remains: ``sq feat`` would still
    dispatch into feature's command tree, which the spec no longer says anything about."""
    _write_override(
        project.squad_dir,
        '[items.feature]\naliases = ["ft"]\n\n[items.task]\naliases = ["feat"]\n',
    )
    errors = _errors(project.squad_dir)
    assert any("duplicate alias" in m for m in errors) is False, errors
    assert any(
        "item 'task': alias 'feat' shadows the built-in `sq feat` alias of the 'feature' command"
        in m
        for m in errors
    ), errors


async def test_the_owner_type_keeps_declaring_its_own_bundled_alias(project, invoke) -> None:
    """`feature` declaring `feat` IS the static table's entry, not a collision with it — the
    bundled spec itself must stay loadable, and so must an override that restates it."""
    _write_override(project.squad_dir, '[items.feature]\naliases = ["feat", "f"]\n')
    assert _errors(project.squad_dir) == []

    linted = await invoke(["workflow", "lint"])
    assert linted.exit_code == 0, linted.output


# ─── direction 2: a bundled alias the spec no longer declares ─────────────────


@pytest.mark.parametrize("alias", _BUNDLED_ALIASES)
async def test_a_dropped_bundled_alias_stops_dispatching(project, invoke, alias: str) -> None:
    _write_override(project.squad_dir, _RENAMED_ALIASES_OVERRIDE)
    result = await invoke([alias, "1", "show"])
    assert result.exit_code == 1, result.output
    assert "not a declared item-type alias" in result.output


@pytest.mark.parametrize("alias", _BUNDLED_ALIASES)
async def test_a_dropped_bundled_alias_stops_creating(project, invoke, alias: str) -> None:
    _write_override(project.squad_dir, _RENAMED_ALIASES_OVERRIDE)
    result = await invoke(["create", alias, "Ghost", "--author", "manager"])
    assert result.exit_code == 1, result.output
    assert "not a declared item-type alias" in result.output


async def test_the_refusal_names_the_alias_the_owner_declares_now(project, invoke) -> None:
    _write_override(project.squad_dir, _RENAMED_ALIASES_OVERRIDE)
    result = await invoke(["feat", "1", "show"])
    assert "'feature' now declares 'ft'" in result.output
    assert "sq feature" in result.output


async def test_the_refusal_answers_help_and_a_bare_invocation_too(project, invoke) -> None:
    """A stale alias must not document itself: its own `--help` is retired so the refusal is
    what every route produces."""
    _write_override(project.squad_dir, _RENAMED_ALIASES_OVERRIDE)
    for args in (["feat"], ["feat", "--help"], ["create", "feat", "--help"]):
        result = await invoke(args)
        assert result.exit_code == 1, f"{args!r}: {result.output}"
        assert "not a declared item-type alias" in result.output


async def test_a_newly_declared_alias_reaches_both_surfaces(project, invoke) -> None:
    """The other half of a rename: the alias the spec DOES declare has to work, on the
    resource group and on `sq create` alike."""
    _write_override(project.squad_dir, _RENAMED_ALIASES_OVERRIDE)
    created = await invoke(["create", "ft", "Login", "--author", "manager"])
    assert created.exit_code == 0, created.output
    num = _feature_num(created.output)

    shown = await invoke(["ft", num, "show", "--json"])
    assert shown.exit_code == 0, shown.output
    assert "Login" in shown.output


# ─── no change for a squad that declares nothing ──────────────────────────────


@pytest.mark.parametrize("alias", _BUNDLED_ALIASES)
async def test_every_bundled_alias_still_dispatches_without_an_override(
    project, invoke, alias: str
) -> None:
    result = await invoke([alias, "--help"])
    assert result.exit_code == 0, result.output
