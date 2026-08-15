"""``add-<kind>`` and ``<kind> <n> update`` bake one ``--<field-code>`` option per declared
field into their Typer parameter list, and for a statically-registered type that happens at
import time against the bundled spec. Rebuilding only when the kind's *name* changed left a
spec that swapped the kind's fields — ``finding``'s ``severity`` for a required ``impact`` —
with a parameter surface describing a spec that no longer exists: ``--severity`` was offered,
accepted and stored for an undeclared field (rendering nowhere, since every badge readout is
derived from ``fields_for``), ``--impact`` did not exist, and the required default never
applied. The sq-rendered body hint meanwhile already advertised ``--impact``.

The service's own ``fields=`` door had the same hole and is gated here too — one refusal, both
doors, mirroring the item axis.
"""

from pathlib import Path

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._rendering._engine import invalidate_squad_dir
from squads._workflow import load_workflow_spec

pytestmark = pytest.mark.anyio

_IMPACT_ON_FINDING = """\
[collections.impact]
label = "Impact"
ordered = true
default = "medium"
badges = [
  { code = "blocker", label = "Blocker" },
  { code = "medium", label = "Medium" },
  { code = "cosmetic", label = "Cosmetic" },
]

[subentity_kinds.finding]
fields = [
  { code = "impact", label = "Impact", collection = "impact", required = true, default = "medium" },
]
"""


def _write_override(squad_dir: Path, body: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{body}", encoding="utf-8"
    )
    invalidate_squad_dir(squad_dir)
    # Prove the override actually loads: the CLI's spec resolution is fail-soft, so a
    # malformed or invalid override degrades silently to the bundled spec and every assertion
    # below would keep passing against bundled vocabulary. Load it eagerly so a broken
    # fixture is a setup error, not a misleading pass.
    load_workflow_spec(squad_dir=squad_dir)


async def _new_review(invoke) -> str:
    created = await invoke(["create", "review", "Sweep", "--author", "manager"])
    assert created.exit_code == 0, created.output
    return created.output.split("REV-")[1].split()[0].lstrip("0")


# ─── the CLI parameter surface ────────────────────────────────────────────────


async def test_add_offers_the_declared_field_and_not_the_bundled_one(project, invoke) -> None:
    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    result = await invoke(["review", num, "add-finding", "--help"])
    assert result.exit_code == 0, result.output
    assert "--impact" in result.output
    assert "--severity" not in result.output


async def test_update_offers_the_declared_field_and_not_the_bundled_one(project, invoke) -> None:
    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    assert (await invoke(["review", num, "add-finding", "Null deref"])).exit_code == 0

    result = await invoke(["review", num, "finding", "F1", "update", "--help"])
    assert result.exit_code == 0, result.output
    assert "--impact" in result.output
    assert "--severity" not in result.output


async def test_the_undeclared_field_flag_is_no_longer_accepted(project, invoke) -> None:
    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    result = await invoke(["review", num, "add-finding", "Null deref", "--severity", "high"])
    assert result.exit_code != 0
    assert "--severity" in result.output


async def test_an_omitted_required_field_applies_its_declared_default(project, invoke) -> None:
    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    assert (await invoke(["review", num, "add-finding", "Null deref"])).exit_code == 0

    shown = await invoke(["review", num, "show", "--json"])
    assert shown.exit_code == 0, shown.output
    assert '"impact": "medium"' in shown.output


async def test_the_declared_field_flag_stores_and_reads_back_through_the_badges_map(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    added = await invoke(["review", num, "add-finding", "Null deref", "--impact", "blocker"])
    assert added.exit_code == 0, added.output

    shown = await invoke(["review", num, "show", "--json"])
    assert '"impact": "blocker"' in shown.output

    updated = await invoke(["review", num, "finding", "F1", "update", "--impact", "cosmetic"])
    assert updated.exit_code == 0, updated.output
    assert '"impact": "cosmetic"' in (await invoke(["review", num, "show", "--json"])).output


async def test_the_rendered_body_hint_names_a_flag_the_cli_accepts(project, invoke) -> None:
    """The hint and the parameter list are two renderings of the same declaration — they used
    to disagree, with the hint right and the CLI wrong."""
    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    written = next(project.squad_dir.glob("reviews/REV-*.md")).read_text(encoding="utf-8")
    assert "--impact medium" in written

    accepted = await invoke(["review", num, "add-finding", "Null deref", "--impact", "medium"])
    assert accepted.exit_code == 0, accepted.output


# ─── the service door ─────────────────────────────────────────────────────────


async def test_the_service_refuses_a_field_the_kind_does_not_declare(project, invoke) -> None:
    """`open_service` (not the `svc` fixture) so the service reads the override written
    after the fixture would have been built."""
    from squads._services._service import open_service

    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    review_id = f"REV-{num}"
    live = open_service(str(project.squad_dir))

    with pytest.raises(SquadsError, match="not a settable field"):
        await live.add_block(review_id, "finding", "X", fields={"severity": "high"})

    assert (await invoke(["review", num, "add-finding", "Real"])).exit_code == 0
    with pytest.raises(SquadsError, match="not a settable field"):
        await live.update_block(review_id, "finding", "F1", fields={"severity": "high"})


async def test_the_service_refuses_a_value_outside_the_declared_collection(project, invoke) -> None:
    from squads._services._service import open_service

    _write_override(project.squad_dir, _IMPACT_ON_FINDING)
    num = await _new_review(invoke)
    live = open_service(str(project.squad_dir))
    with pytest.raises(SquadsError, match="invalid impact"):
        await live.add_block(f"REV-{num}", "finding", "X", fields={"impact": "enormous"})


# ─── an unmodified squad is unchanged ─────────────────────────────────────────


async def test_a_plain_squad_keeps_the_bundled_severity_surface(project, invoke) -> None:
    num = await _new_review(invoke)
    help_result = await invoke(["review", num, "add-finding", "--help"])
    assert "--severity" in help_result.output
    assert "--impact" not in help_result.output

    added = await invoke(["review", num, "add-finding", "Null deref", "--severity", "high"])
    assert added.exit_code == 0, added.output
    assert '"severity": "high"' in (await invoke(["review", num, "show", "--json"])).output

    defaulted = await invoke(["review", num, "add-finding", "Second"])
    assert defaulted.exit_code == 0, defaulted.output
    assert '"severity": "medium"' in (await invoke(["review", num, "show", "--json"])).output
