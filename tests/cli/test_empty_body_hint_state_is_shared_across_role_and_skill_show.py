"""``squads._views.empty_body_hint_state`` is the one predicate ``sq role show`` and ``sq skill
show`` both read to pick an empty body's hint — table-driven here over the three states it can
return, for both commands, so the two groups cannot silently disagree about which one applies.

Before this fix, each command derived its hint from its own ad hoc "is the view declared"
boolean, which cannot tell state 2 (declared, drift still outstanding — the one state ``sq
sync`` genuinely fixes) apart from state 3 (declared, no drift left to trigger the backfill —
where ``sq sync`` is provably a no-op). Both read as "declared" to that boolean, so both got the
same "run `sq sync` to populate it" sentence — false in state 3, since the backfill this
sentence promises only ever runs on an outstanding version drift. This module's state-3 cases
must fail before the fix (the old code always printed the state-2 sentence for a declared view)
and pass after.
"""

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
    """Console output can wrap a multi-word phrase across a line boundary — collapse before a
    substring check, per the project's own line-wrap lesson."""
    return " ".join(text.split())


def _empty_body(svc, item) -> None:
    path = item_file(svc.paths, item)
    text = replace_section(path.read_text(encoding="utf-8"), markers.BODY, "")
    path.write_text(text, encoding="utf-8")


def _stamp_older_squads_version(squad_dir: Path) -> None:
    """Rewrite ``.squads.toml``'s ``squads_version`` to an older plain release — puts the
    version-drift backfill's own trigger, and this predicate's second question, in the
    'outstanding' branch. ``schema_version`` is left untouched; no migration is wanted here."""
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


async def test_role_view_declared_with_drift_outstanding_says_run_sync(svc, invoke) -> None:
    role = await svc.activate_role("reviewer")
    _empty_body(svc, role)
    _stamp_older_squads_version(svc.paths.squad_dir)

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE in _collapsed(r.output)


async def test_role_view_declared_with_no_drift_does_not_say_run_sync(svc, invoke) -> None:
    """The state the old code could not distinguish: the view is declared and nothing has
    backfilled the tag, but there is no version drift left to trigger the backfill — ``sq
    sync`` is a no-op here. Must fail before the fix (old code always printed the state-2
    sentence for any declared view)."""
    role = await svc.activate_role("reviewer")
    _empty_body(svc, role)
    # No _stamp_older_squads_version call: the fixture squad is already stamped at the
    # running version, so there is nothing outstanding for sync's own trigger to fire on.

    r = await invoke(["role", "reviewer", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in _collapsed(r.output)
    assert "sq repair" in r.output
    assert "view add role_definition" in _collapsed(r.output)


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
    """The state the old code could not distinguish, on the skill side. Must fail before the
    fix for the same reason as its role-group sibling above."""
    await svc.seed_bundled_skills()
    skill = await svc.roster_item("skill", "squads")
    assert skill is not None
    _empty_body(svc, skill)

    r = await invoke(["skill", "squads", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert _SYNC_SENTENCE not in _collapsed(r.output)
    assert "sq repair" in r.output
    assert "view add squads_skill" in _collapsed(r.output)
