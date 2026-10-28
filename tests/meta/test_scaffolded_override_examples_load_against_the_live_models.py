"""Repo-hygiene gate: every worked example a ``sq override scaffold`` verb writes must still load
against the models that are actually shipped."""

from pathlib import Path

import pytest

from squads._interactions import _role_guidance as role_guidance
from squads._interactions._loader import load_playbook
from squads._language import WorkingLanguage
from squads._overrides import _service as overrides
from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from tests._helpers import role_of

#: The line that opens each scaffold's worked example, and the ruled line that closes it. Both
#: are literal in the bodies; matching on them keeps the activator from touching the surrounding
#: prose, which is deliberately not TOML.
_EXAMPLE_OPEN = "# --- Worked example"
_EXAMPLE_CLOSE = "# ----------------"


def _activate_example(body: str) -> str:
    """The worked example as an adopter would activate it: the block between the two ruled
    lines, with one comment prefix stripped from every line. A line that is still a comment
    afterwards (``# # Custom lifecycle: …``) was a comment *inside* the example and stays one.
    """
    lines = body.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith(_EXAMPLE_OPEN))
    except StopIteration:  # pragma: no cover - a scaffold with no example
        return ""
    end = next(
        (
            i
            for i, line in enumerate(lines[start + 1 :], start + 1)
            if line.startswith(_EXAMPLE_CLOSE)
        ),
        len(lines),
    )
    out = [
        line[2:] if line.startswith("# ") else line.removeprefix("#")
        for line in lines[start + 1 : end]
    ]
    return "\n".join(out) + "\n"


def _write_override(squad_dir: Path, relative: str, text: str) -> None:
    dest = squad_dir / ".overrides" / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")


def test_the_workflow_scaffolds_worked_example_builds_a_valid_spec(tmp_path) -> None:
    activated = _activate_example(overrides._WORKFLOW_SCAFFOLD_BODY)
    assert "[items.incident]" in activated, "the activator no longer finds the worked example"
    _write_override(tmp_path, "workflow.toml", activated)

    spec = load_workflow_spec(squad_dir=tmp_path)

    assert "incident" in spec.items
    assert spec.items["incident"].lifecycle == "incident"


def test_the_workflow_scaffolds_worked_example_declares_a_valid_view(tmp_path) -> None:
    """The scaffold's `[views]` example resolves against declared vocabulary."""
    activated = _activate_example(overrides._WORKFLOW_SCAFFOLD_BODY)
    assert "[views.related_incidents]" in activated, "the view example is missing"
    _write_override(tmp_path, "workflow.toml", activated)

    spec = load_workflow_spec(squad_dir=tmp_path)

    view = spec.views["related_incidents"]
    assert view.source.kind == "ref"
    assert view.source.name in spec.ref_kinds
    assert view.transform is not None
    assert view.transform.path == "transforms/related_incidents.py"


def test_the_workflow_scaffolds_worked_example_view_refuses_cleanly_without_a_template(
    tmp_path,
) -> None:
    """Structural validity."""
    from squads import _clock as clock
    from squads import _views as views
    from squads._errors import SquadsError
    from squads._models._item import Item

    activated = _activate_example(overrides._WORKFLOW_SCAFFOLD_BODY)
    _write_override(tmp_path, "workflow.toml", activated)
    spec = load_workflow_spec(squad_dir=tmp_path)  # the example must still load on its own

    now = clock.now()
    incident = Item(
        sequence_id=1,
        type="incident",
        title="An incident",
        slug="an-incident",
        status="Triage",
        path="incidents/x1.md",
        created_at=now,
        updated_at=now,
        prefix="INC",
    )
    with pytest.raises(SquadsError, match=r"templates/views/related_incidents.md.j2"):
        views.render_source_view(
            "related_incidents",
            [],
            incident,
            spec,
            None,
            WorkingLanguage("en", "English"),
            from_squad=None,
        )


def test_the_workflow_scaffolds_example_demonstrates_the_field_that_drives_status_behaviour(
    tmp_path,
) -> None:
    """Not a style point."""
    activated = _activate_example(overrides._WORKFLOW_SCAFFOLD_BODY)
    _write_override(tmp_path, "workflow.toml", activated)

    spec = load_workflow_spec(squad_dir=tmp_path)

    declared = {name: spec.statuses[name].role for name in ("Triage", "Mitigating", "Resolved")}
    assert all(role is not None for role in declared.values()), declared
    assert len(set(declared.values())) > 1, "the example should show more than one role in use"


def test_the_playbook_scaffolds_worked_example_loads(tmp_path) -> None:
    activated = _activate_example(overrides._PLAYBOOK_SCAFFOLD_BODY)
    assert "[types.task]" in activated, "the activator no longer finds the worked example"
    _write_override(tmp_path, "playbook.toml", activated)

    playbook = load_playbook(spec=load_workflow_spec(), squad_dir=tmp_path)

    slugs = [guide.slug for guide in playbook.types["task"].roles]
    assert "architect" in slugs
    assert len(slugs) > 1, "the append idiom must keep the bundled guides, not replace them"

    # The second worked example puts a role in the type's create-lane; the lane it advertises
    # must actually be the one the engine derives, or the scaffold teaches a no-op.
    assert "[types.bug]" in activated, "the create-lane example is missing from the scaffold"
    assert "bug" in role_guidance.allowed_create_types(role_of("devops"), bundled_spec(), playbook)
