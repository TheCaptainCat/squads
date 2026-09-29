"""``sq role show`` and ``sq skill show`` pick an empty body's hint from the same predicate,
table-driven here over its three states so the two commands can never disagree."""

import re
from pathlib import Path

import pytest

from squads._index._resolver import item_file
from squads._models import _markers as markers
from squads._sections import replace_section
from squads._services import _service as service
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_SYNC_SENTENCE = "run `sq sync` to populate it"


def _collapsed(text: str) -> str:
    """Collapse whitespace so a wrapped multi-word phrase still matches a substring check."""
    return " ".join(text.split())


def _empty_body(svc, item) -> None:
    path = item_file(svc.paths, item)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")


def _stamp_older_squads_version(squad_dir: Path) -> None:
    """Rewrite ``.squads.toml``'s ``squads_version`` to an older release, leaving
    ``schema_version`` untouched, so version drift is outstanding."""
    toml_path = squad_dir.parent / ".squads.toml"
    text = toml_path.read_text(encoding="utf-8")
    text = re.sub(r'squads_version = ".*"', 'squads_version = "0.1.0"', text)
    toml_path.write_text(text, encoding="utf-8")


_DROP_ROLE_DEFINITION = """\
[selected]
views = ["milestone_rollup", "squads_skill", "greeting_skill", "memory_skill", "item_skill"]
"""

_DROP_SQUADS_SKILL = """\
[selected]
views = ["milestone_rollup", "role_definition", "greeting_skill", "memory_skill", "item_skill"]
"""


def _write_override(squad_dir: Path, content: str) -> None:
    from squads import __version__

    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


# --------------------------------------------------------------------------- role group


async def test_role_view_undeclared_names_the_view_not_sync(svc, invoke) -> None:
    _write_override(svc.paths.squad_dir, _DROP_ROLE_DEFINITION)
    spec = load_workflow_spec(squad_dir=svc.paths.squad_dir)
    declared = service.Service(svc.paths, spec=spec)
    role = await declared.activate_role("reviewer")
    _empty_body(declared, role)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in r.output
    assert "role_definition" in r.output
    assert "not declared" in r.output
    assert "sq role reviewer view disable role_definition" in _collapsed(r.output)
    assert "<slug>" not in _collapsed(r.output)


async def test_role_view_disabled_names_the_real_role_in_the_re_enable_command(svc, invoke) -> None:
    """The disabled-view hint names the real role slug, never a literal `<slug>` placeholder."""
    role = await svc.activate_role("reviewer")
    disabled = await svc.disable_view(role.id, "role_definition")
    assert disabled is True

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "disabled" in r.output
    assert "sq role reviewer view add role_definition" in _collapsed(r.output)
    assert "<slug>" not in _collapsed(r.output)


async def test_role_view_declared_with_drift_outstanding_says_run_sync(svc, invoke) -> None:
    role = await svc.activate_role("reviewer")
    _empty_body(svc, role)
    _stamp_older_squads_version(svc.paths.squad_dir)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE in _collapsed(r.output)


async def test_role_view_declared_with_no_drift_does_not_say_run_sync(svc, invoke) -> None:
    """With no version drift outstanding, ``sq sync`` is a no-op, so the hint names the role's
    real authoring surface instead."""
    role = await svc.activate_role("reviewer")
    _empty_body(svc, role)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in _collapsed(r.output)
    assert "roles.toml" in r.output
    assert "sq role reviewer view add role_definition" in _collapsed(r.output)


# --------------------------------------------------------------------------- skill group


async def test_skill_view_undeclared_names_the_view_not_sync(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    _write_override(svc.paths.squad_dir, _DROP_SQUADS_SKILL)
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in r.output
    assert "squads_skill" in r.output
    assert "not declared" in r.output


async def test_skill_view_declared_with_drift_outstanding_says_run_sync(svc, invoke) -> None:
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)
    _stamp_older_squads_version(svc.paths.squad_dir)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE in _collapsed(r.output)


async def test_skill_view_declared_with_no_drift_does_not_say_run_sync(svc, invoke) -> None:
    """With no version drift outstanding, the skill's hint names the playbook overrides."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in _collapsed(r.output)
    assert "`.overrides/playbook.toml`" in r.output
    assert "view add squads_skill" in _collapsed(r.output)


@pytest.mark.parametrize(
    ("slug", "view_name", "expected", "unexpected"),
    [
        pytest.param(
            "greeting",
            "greeting_skill",
            "its `.overrides/templates/views/greeting_skill.md.j2` view template override",
            "playbook.toml",
            id="self-sourced-permanently-system",
        ),
        pytest.param(
            "sq-memory",
            "memory_skill",
            "its `.overrides/templates/views/memory_skill.md.j2` view template override",
            "playbook.toml",
            id="self-sourced-permanently-system-2",
        ),
        pytest.param(
            "squads",
            "squads_skill",
            "`.overrides/playbook.toml`",
            "[types.",
            id="playbook-sourced-no-type-lane",
        ),
        pytest.param(
            "sq-bug",
            "item_skill",
            "the `[types.bug]` lane in `.overrides/playbook.toml`",
            "view template override",
            id="playbook-sourced-per-item-type-lane",
        ),
    ],
)
async def test_skill_no_drift_hint_names_the_same_surface_as_the_refusal(
    svc, invoke, slug, view_name, expected, unexpected
) -> None:
    """The show hint and the body-write refusal read the same authoring-surface predicate, so
    they always name the same surface, including for the permanently-system skills."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", slug)
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", slug, "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in _collapsed(r.output)
    assert expected in _collapsed(r.output), r.output
    assert unexpected not in _collapsed(r.output), r.output
    assert f"sq skill {slug} view add {view_name}" in _collapsed(r.output)
