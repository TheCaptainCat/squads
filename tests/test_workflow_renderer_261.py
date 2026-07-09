"""TASK-000261 — Spec-derived sq workflow renderer and CLAUDE.md / AGENTS.md sync.

Covers:
- AC#3: sq workflow output for a custom squad includes the custom type's prefix,
  auto-linearized lifecycle, and aliases; the ref-kinds / retype / remove-vs-cancel
  sections are byte-identical static prose (never spec-driven).
- AC#4: sq sync regenerates CLAUDE.md and AGENTS.md workflow sections and the
  squads skill to include the custom type.
- AC#7/#8: non-custom squad output is byte-identical to HEAD goldens (spec-derived
  renderer produces the same text as the old TYPE_ALIASES approach).
- Static/dynamic split integrity: static prose sections are immutable regardless of spec.
"""

from pathlib import Path
from typing import Any

import pytest

from squads._rendering._engine import render
from squads._workflow import bundled_spec, linearize_lifecycle
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, Lifecycle, WorkflowSpec

pytestmark = pytest.mark.anyio

# ---------------------------------------------------------------------------
# Helpers — build a spec with a custom 'incident' type
# ---------------------------------------------------------------------------

_INCIDENT_TYPE = "incident"
_INCIDENT_PREFIX = "INC"
_INCIDENT_ALIAS = "inc"
_OVERRIDE_TOML = """\
[lifecycles.triage]
initial = "Open"

[lifecycles.triage.transitions]
Open = ["Done", "WontFix"]
Done = []
WontFix = ["Open"]

[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "triage"
aliases = ["inc"]
"""

# The expected auto-linearized lifecycle for the triage machine above.
# Open → Done (spine); WontFix is a side state reachable from Open.
_EXPECTED_INCIDENT_LIFECYCLE = "Open → Done (+ WontFix)"


def _spec_with_incident() -> WorkflowSpec:
    """Return the bundled spec extended with a minimal 'incident' custom type."""
    base = load_workflow_spec()
    triage = Lifecycle(
        initial="Open",
        transitions={
            "Open": ["Done", "WontFix"],
            "Done": [],
            "WontFix": ["Open"],
        },
    )
    incident_spec = ItemSpec(
        prefix=_INCIDENT_PREFIX,
        folder="incidents",
        lifecycle="triage",
        aliases=[_INCIDENT_ALIAS],
    )
    new_lifecycles = dict(base.lifecycles)
    new_lifecycles["triage"] = triage
    new_items = dict(base.items)
    new_items[_INCIDENT_TYPE] = incident_spec
    new_prefix_to_type = dict(base.prefix_to_type)
    new_prefix_to_type[_INCIDENT_PREFIX] = _INCIDENT_TYPE
    new_alias_to_type = dict(base.alias_to_type)
    new_alias_to_type[_INCIDENT_ALIAS] = _INCIDENT_TYPE
    return WorkflowSpec.model_validate(
        {
            "items": new_items,
            "statuses": base.statuses,
            "lifecycles": new_lifecycles,
            "prefix_to_type": new_prefix_to_type,
            "alias_to_type": new_alias_to_type,
            "collections": base.collections,
            "subentity_kinds": base.subentity_kinds,
        }
    )


def _write_override(squad_dir: Path, content: str = _OVERRIDE_TOML) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Static/dynamic split — workflow_static.md.j2
# ---------------------------------------------------------------------------

# The three stability-contract sections that must NEVER become spec-driven.
_STATIC_SECTIONS = [
    ("## Retype", "Retype section (stability contract)"),
    ("## Remove vs. Cancel", "Remove vs. Cancel section (stability contract)"),
    ("## Ref kinds", "Ref kinds section (stability contract)"),
]

# Exact first lines from the static sections — these must be byte-identical
# regardless of whether a custom type is present.
_STATIC_RETYPE_INTRO = (
    "Reclassify a work item to a different type — the sequence number (and durable identity) is"
)
_STATIC_REFKINDS_INTRO = (
    "The vocabulary is closed — exactly eight kinds, no custom extensions in 1.0."
)


class TestStaticDynamicSplit:
    """Verify the static/dynamic split in workflow.md.j2 (AC#3 structural requirement)."""

    def test_static_sections_present_in_bundled_spec(self) -> None:
        """Static sections are present and intact for the bundled (non-custom) spec."""
        rendered = render("workflow.md.j2", spec=bundled_spec())
        for header, desc in _STATIC_SECTIONS:
            assert header in rendered, f"{desc} missing from bundled-spec render"

    def test_static_sections_present_in_custom_spec(self) -> None:
        """Static sections remain present and intact when a custom type is in the spec."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        for header, desc in _STATIC_SECTIONS:
            assert header in rendered, f"{desc} missing from custom-spec render"

    def test_static_section_prose_identical_bundled_vs_custom(self) -> None:
        """Static-section prose is byte-identical whether or not a custom type exists.

        This is the core proof of AC#3: the stability-contract sections are untouched
        by spec customisation — EXCEPT the single "Valid targets" retype-list line, which
        TASK-000279 deliberately lifted out of the static partial into a spec-derived loop
        (custom types ARE retypeable). Comparison starts right after that line, at the
        "Status behaviour" paragraph, which — like the rest of Retype/Remove-vs-Cancel/Ref
        kinds — must NEVER be spec-driven.
        """
        bundled_rendered = render("workflow.md.j2", spec=bundled_spec())
        custom_rendered = render("workflow.md.j2", spec=_spec_with_incident())

        # Extract from "**Status behaviour:**" (just after the spec-derived target-list line)
        # to end for both renders and compare.
        marker = "**Status behaviour:**"
        status_start_bundled = bundled_rendered.find(marker)
        status_start_custom = custom_rendered.find(marker)
        assert status_start_bundled != -1, f"{marker!r} not found in bundled render"
        assert status_start_custom != -1, f"{marker!r} not found in custom render"

        static_bundled = bundled_rendered[status_start_bundled:]
        static_custom = custom_rendered[status_start_custom:]
        assert static_bundled == static_custom, (
            "Static prose sections differ between bundled and custom spec renders.\n"
            "The stability-contract sections (Retype mechanics/Remove vs. Cancel/Ref kinds) "
            "must NEVER be spec-driven."
        )

    def test_retype_target_list_includes_custom_type(self) -> None:
        """TASK-000279: the 'Valid targets' retype line IS spec-derived — a custom type appears."""
        rendered = render("workflow.md.j2", spec=_spec_with_incident())
        assert "Valid targets:" in rendered
        line = next(ln for ln in rendered.splitlines() if ln.startswith("Valid targets:"))
        assert f"`{_INCIDENT_TYPE}`" in line, (
            f"Custom type {_INCIDENT_TYPE!r} missing from spec-derived retype target list"
        )
        for builtin in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
            assert f"`{builtin}`" in line, f"Built-in type {builtin!r} missing from target list"

    def test_retype_section_exact_intro(self) -> None:
        """Retype section opens with the exact stability-contract intro line."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        assert _STATIC_RETYPE_INTRO in rendered, (
            "Retype intro prose changed — stability-contract text must not be modified"
        )

    def test_refkinds_section_exact_intro(self) -> None:
        """Ref kinds section opens with the exact closed-vocabulary statement."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        assert _STATIC_REFKINDS_INTRO in rendered, (
            "Ref kinds intro prose changed — stability-contract text must not be modified"
        )


# ---------------------------------------------------------------------------
# AC#3 — Custom type appears in workflow cheatsheet
# ---------------------------------------------------------------------------


class TestCustomTypeInWorkflowCheatsheet:
    """AC#3: sq workflow output includes the custom type's prefix, lifecycle, and aliases."""

    def test_custom_type_alias_in_table(self) -> None:
        """The alias table contains the custom type's canonical name and alias."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        # The alias table row for 'incident' must be present.
        assert "| `incident` |" in rendered, "Custom type 'incident' missing from alias table"
        assert "`inc`" in rendered, "Custom alias 'inc' missing from alias table"

    def test_custom_type_example_in_table(self) -> None:
        """The alias table row for the custom type contains an example command."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        assert "`sq inc <n> show`" in rendered, (
            "Example command for custom alias 'inc' missing from alias table"
        )

    def test_bundled_types_still_present(self) -> None:
        """All 7 built-in type aliases are still present alongside the custom type."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        for canonical, alias in [
            ("epic", "e"),
            ("feature", "f"),
            ("task", "t"),
            ("bug", "b"),
            ("decision", "d"),
            ("review", "r"),
            ("guide", "g"),
        ]:
            assert f"| `{canonical}` |" in rendered, (
                f"Built-in type '{canonical}' missing from alias table"
            )
            assert f"`{alias}`" in rendered, f"Built-in alias '{alias}' missing from alias table"

    def test_lifecycle_linearized_from_spec(self) -> None:
        """The auto-linearized lifecycle string for the custom type is correct."""
        spec = _spec_with_incident()
        machine = spec.machine_for(_INCIDENT_TYPE)
        lifecycle_str = linearize_lifecycle(machine)
        assert lifecycle_str == _EXPECTED_INCIDENT_LIFECYCLE, (
            f"Unexpected lifecycle string: {lifecycle_str!r} "
            f"(expected {_EXPECTED_INCIDENT_LIFECYCLE!r})"
        )

    def test_no_ansi_in_rendered_output(self) -> None:
        """No ANSI escape codes in the raw rendered markdown (pre-Rich)."""
        spec = _spec_with_incident()
        rendered = render("workflow.md.j2", spec=spec)
        assert "\x1b[" not in rendered, "ANSI escape codes found in raw template output"


# ---------------------------------------------------------------------------
# AC#7 / AC#8 — Byte-identical for non-custom squads
# ---------------------------------------------------------------------------


class TestByteIdenticalForBundledSpec:
    """AC#7/#8: non-custom squad output is byte-identical to the HEAD golden."""

    def test_workflow_cheatsheet_matches_golden(self) -> None:
        """workflow.md.j2 with bundled spec is byte-identical to the golden."""
        from pathlib import Path

        golden_path = Path(__file__).parent / "goldens" / "workflow_cheatsheet.txt"
        assert golden_path.exists(), f"Golden file missing: {golden_path}"
        expected = golden_path.read_text(encoding="utf-8")
        actual = render("workflow.md.j2", spec=bundled_spec())
        assert actual == expected, (
            "workflow.md.j2 with bundled spec is not byte-identical to the golden. "
            "AC#7/#8 requires zero change for non-custom squads."
        )

    def test_agents_section_matches_golden(self) -> None:
        """agents_section.md.j2 with bundled spec is byte-identical to the golden."""
        from pathlib import Path

        from squads._backends._base import OperatorView, RoleView

        golden_path = Path(__file__).parent / "goldens" / "agents_md_section.txt"
        assert golden_path.exists(), f"Golden file missing: {golden_path}"
        expected = golden_path.read_text(encoding="utf-8")

        pinned_roster = [
            RoleView(
                slug="manager", full_name="Catherine Manager", title="Manager", is_default=True
            ),
            RoleView(
                slug="architect", full_name="Robert Architect", title="Architect", is_default=False
            ),
            RoleView(
                slug="tech-lead", full_name="Olivia Lead", title="Tech lead", is_default=False
            ),
            RoleView(
                slug="reviewer", full_name="Paul Reviewer", title="Code reviewer", is_default=False
            ),
            RoleView(slug="qa", full_name="Mara Tester", title="QA engineer", is_default=False),
            RoleView(
                slug="devops", full_name="Hugo Ops", title="DevOps engineer", is_default=False
            ),
            RoleView(
                slug="product-owner",
                full_name="Nina Product",
                title="Product owner",
                is_default=False,
            ),
            RoleView(
                slug="tech-writer",
                full_name="Theo Writer",
                title="Technical writer",
                is_default=False,
            ),
            RoleView(
                slug="python-dev",
                full_name="Elias Python",
                title="Python developer",
                is_default=False,
            ),
        ]
        pinned_operators = [OperatorView(slug="op-pierre", full_name="Pierre Chat")]

        actual = render(
            "agents_md/agents_section.md.j2",
            squad_dir="squads",
            roles=[
                {
                    "full_name": r.full_name,
                    "title": r.title,
                    "slug": r.slug,
                    "mission": "",
                    "responsibilities": [],
                }
                for r in pinned_roster
            ],
            operators=[{"full_name": o.full_name, "slug": o.slug} for o in pinned_operators],
            spec=bundled_spec(),
        )
        assert actual == expected, (
            "agents_section.md.j2 with bundled spec is not byte-identical to the golden. "
            "AC#7/#8 requires zero change for non-custom squads."
        )


# ---------------------------------------------------------------------------
# AC#4 — sq sync regenerates CLAUDE.md and AGENTS.md for custom type
# ---------------------------------------------------------------------------


async def test_sync_agents_md_includes_custom_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any
) -> None:
    """AC#4: sq sync regenerates AGENTS.md workflow section to include the custom type.

    After adding an 'incident' type and running sq sync, the AGENTS.md file must contain
    the 'incident' entry in the alias table.  Uses the agents_md backend so AGENTS.md is
    written.
    """
    from squads._services import _service as service

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(
        root=tmp_path,
        roles_spec="minimal",
        backend=["agents_md"],
        _skip_skill_seed=True,
    )
    paths = init_result.paths
    _write_override(paths.squad_dir)

    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    agents_md = paths.root / "AGENTS.md"
    assert agents_md.is_file(), "AGENTS.md not written by sq sync (is agents_md backend active?)"
    text = agents_md.read_text(encoding="utf-8")

    # Custom type must appear in the alias table.
    assert "incident" in text, "Custom type 'incident' not found in AGENTS.md after sync"
    assert "`inc`" in text, "Custom alias 'inc' not found in AGENTS.md after sync"

    # Static sections must still be present.
    for header, desc in _STATIC_SECTIONS:
        assert header in text, f"{desc} missing from AGENTS.md after sync"


async def test_sync_claude_md_includes_custom_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any
) -> None:
    """AC#4: sq sync regenerates CLAUDE.md to include the custom type in the squads skill.

    The squads skill body is embedded in CLAUDE.md via the managed section; it includes
    workflow.md.j2 which must show the custom type's alias table entry.
    """
    from squads._services import _service as service

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(root=tmp_path, roles_spec="minimal", _skip_skill_seed=True)
    paths = init_result.paths
    _write_override(paths.squad_dir)

    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    svc = service.Service(paths, spec=spec)
    await svc.sync()

    # The squads skill body is at agents/skills/squads.md (pre-stamp legacy path) or
    # agents/skills/SKILL-NNNNNN-squads.md (convention-name after seeding).
    skills_folder = paths.squad_dir / "agents" / "skills"
    convention_files = list(skills_folder.glob("SKILL-*-squads.md"))
    legacy_file = skills_folder / "squads.md"
    skill_file = convention_files[0] if convention_files else legacy_file
    assert skill_file.is_file(), f"squads skill body file not found under {skills_folder}"

    skill_text = skill_file.read_text(encoding="utf-8")
    # The squads skill includes workflow.md.j2 which should contain the custom type.
    assert "incident" in skill_text, (
        "Custom type 'incident' not found in squads skill body after sync"
    )
    assert "`inc`" in skill_text, "Custom alias 'inc' not found in squads skill body after sync"


async def test_sync_agents_md_static_sections_intact_after_custom_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, frozen_time: Any
) -> None:
    """Static sections (Retype/Remove vs. Cancel/Ref kinds) survive custom type sync.

    AC#3: the stability-contract prose must be byte-identical static text and must
    not be affected by adding a custom type to the spec — EXCEPT the spec-derived
    "Valid targets" retype-list line (TASK-000279), which is expected to gain the
    custom type. Uses the agents_md backend.
    """
    from squads._services import _service as service

    monkeypatch.chdir(tmp_path)
    init_result = await service.init(
        root=tmp_path,
        roles_spec="minimal",
        backend=["agents_md"],
        _skip_skill_seed=True,
    )
    paths = init_result.paths

    # First sync without custom types.
    svc_bundled = service.Service(paths)
    await svc_bundled.sync()
    agents_md_before = (paths.root / "AGENTS.md").read_text(encoding="utf-8")

    # Add the custom type and sync again.
    _write_override(paths.squad_dir)
    spec = load_workflow_spec(squad_dir=paths.squad_dir)
    svc_custom = service.Service(paths, spec=spec)
    await svc_custom.sync()
    agents_md_after = (paths.root / "AGENTS.md").read_text(encoding="utf-8")

    # Static sections must be present and byte-identical in both renders.
    for header, desc in _STATIC_SECTIONS:
        assert header in agents_md_before, f"{desc} missing before custom type sync"
        assert header in agents_md_after, f"{desc} missing after custom type sync"

    # Extract static blocks from both versions and compare.  Start right after the
    # spec-derived "Valid targets" line (TASK-000279): its content is *expected* to
    # differ once the custom type is added; everything else in Retype/Remove-vs-Cancel/
    # Ref-kinds must stay byte-identical.
    def _extract_static(text: str) -> str:
        """Extract from '**Status behaviour:**' to end of managed section."""
        idx = text.find("**Status behaviour:**")
        if idx == -1:
            return ""
        end_marker = "<!-- squads:end -->"
        end_idx = text.find(end_marker, idx)
        return text[idx:end_idx] if end_idx != -1 else text[idx:]

    # The spec-derived "Valid targets" line, by contrast, IS expected to pick up the
    # custom type (TASK-000279).
    assert "`incident`" not in agents_md_before, "custom type leaked before it was added"
    assert (
        "Valid targets:" in agents_md_after
        and "`incident`" in agents_md_after.split("Valid targets:")[1].splitlines()[0]
    ), "custom type missing from spec-derived retype target list after sync"

    static_before = _extract_static(agents_md_before)
    static_after = _extract_static(agents_md_after)
    assert static_before == static_after, (
        "Static prose sections changed after adding a custom type. "
        "The stability-contract sections must be byte-identical regardless of spec customisation."
    )


# ---------------------------------------------------------------------------
# CLI smoke: sq workflow output includes custom type when spec has it
# ---------------------------------------------------------------------------


def test_sq_workflow_cli_includes_custom_type(
    runner: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI smoke: sq workflow output includes the custom type's alias row (AC#3)."""
    from squads._cli import app

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    _write_override(tmp_path / "squads")

    result = runner.invoke(app, ["workflow", "show"])
    assert result.exit_code == 0, f"sq workflow show failed:\n{result.output}"
    assert "incident" in result.output, "Custom type 'incident' missing from sq workflow output"
    assert "inc" in result.output, "Custom alias 'inc' missing from sq workflow output"


def test_sq_workflow_cli_static_sections_present(
    runner: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI smoke: static sections are present in sq workflow output (AC#3)."""
    from squads._cli import app

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])
    _write_override(tmp_path / "squads")

    result = runner.invoke(app, ["workflow", "show"])
    assert result.exit_code == 0, f"sq workflow show failed:\n{result.output}"
    # Rich renders the Markdown so header text may be bold/plain — check for key phrases.
    assert "Retype" in result.output, "Retype section missing from sq workflow output"
    assert "Remove vs. Cancel" in result.output or "Remove" in result.output, (
        "Remove vs. Cancel section missing"
    )
    assert "Ref kinds" in result.output, "Ref kinds section missing from sq workflow output"


def test_sq_workflow_cli_non_custom_unchanged(
    runner: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI smoke: sq workflow output for a non-custom squad is unchanged (AC#7)."""
    from squads._cli import app

    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "--no-seed-skills", "--roles", "minimal"])

    result = runner.invoke(app, ["workflow", "show"])
    assert result.exit_code == 0, f"sq workflow show failed:\n{result.output}"
    # All 7 built-in types present; no custom type leakage.
    for t in ("epic", "feature", "task", "bug", "decision", "review", "guide"):
        assert t in result.output, f"Built-in type '{t}' missing from sq workflow output"
    assert "incident" not in result.output, "Custom type 'incident' leaked into non-custom output"
