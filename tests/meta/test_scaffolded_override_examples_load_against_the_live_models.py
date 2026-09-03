"""Repo-hygiene gate: every worked example a ``sq override scaffold`` verb writes must still
load against the models that are actually shipped.

The scaffolded file is an adopter's *first contact* with the override mechanism, and it tells
them to uncomment and edit to activate. The workflow example told them exactly that while
declaring ``terminal = false`` on three statuses — a key ``StatusSpec`` had stopped having, and
under ``extra="forbid"`` following the file's own instruction failed closed with a raw pydantic
dump. One stale key, no test anywhere: the scaffold bodies are string constants, so nothing
about a model change makes one of them fail, and nothing reads them except the adopter.

So the examples are activated (comment prefix stripped inside the worked-example block) and run
through the real loader for their document. A model field renamed or retired now reddens here
instead of in the adopter's terminal.
"""

from pathlib import Path

import pytest

from squads import _interactions as interactions
from squads._interactions._loader import load_playbook
from squads._overrides import _service as overrides
from squads._roles._catalog import get_catalog
from squads._roles._resolver import resolve_role
from squads._workflow._loader import load_workflow_spec

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
    """The scaffold's ``[views]`` example must resolve against declared vocabulary the same
    way the merged spec requires of any project-declared view — an example that failed this
    would teach the adopter a shape ``sq workflow lint`` rejects on the very next run."""
    activated = _activate_example(overrides._WORKFLOW_SCAFFOLD_BODY)
    assert "[views.related_incidents]" in activated, "the view example is missing"
    _write_override(tmp_path, "workflow.toml", activated)

    spec = load_workflow_spec(squad_dir=tmp_path)

    view = spec.views["related_incidents"]
    assert view.source.kind == "ref"
    assert view.source.name in spec.ref_kinds
    assert {f.code for f in view.fields} >= {"id", "status", "title"}


def test_the_workflow_scaffolds_worked_example_view_refuses_cleanly_without_a_template(
    tmp_path,
) -> None:
    """Structural validity (the sibling test above) is not the same as usable end to end: the
    scaffold's view example ships no presentation template, so rendering it is the one failure
    ``load_workflow_spec`` can never see. The comment this scaffold now carries about needing
    one exists because, before it did, an adopter who uncommented and rendered the example hit
    a raw ``jinja2.TemplateNotFound`` traceback rather than a clean, actionable error — the
    exact shape this asserts stays fixed."""
    from squads import _views as views
    from squads._errors import SquadsError

    activated = _activate_example(overrides._WORKFLOW_SCAFFOLD_BODY)
    _write_override(tmp_path, "workflow.toml", activated)
    load_workflow_spec(squad_dir=tmp_path)  # the example must still load on its own

    empty_projection = views.Projection(fields=[], group_by=None, groups=[])
    with pytest.raises(SquadsError, match=r"templates/views/related_incidents.md.j2"):
        views.render_view("related_incidents", empty_projection)


def test_the_workflow_scaffolds_example_demonstrates_the_field_that_drives_status_behaviour(
    tmp_path,
) -> None:
    """Not a style point. ``role`` is the field every status behaviour resolves through —
    settled, hidden, colour, live — so an example that declares statuses without one teaches
    the adopter to leave every custom status on the fallback role by omission."""
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

    playbook = load_playbook(get_catalog(), spec=load_workflow_spec(), squad_dir=tmp_path)

    slugs = [guide.slug for guide in playbook.types["task"].roles]
    assert "architect" in slugs
    assert len(slugs) > 1, "the append idiom must keep the bundled guides, not replace them"

    # The second worked example puts a role in the type's create-lane; the lane it advertises
    # must actually be the one the engine derives, or the scaffold teaches a no-op.
    assert "[types.bug]" in activated, "the create-lane example is missing from the scaffold"
    assert "bug" in interactions.allowed_create_types("devops", playbook=playbook)


@pytest.mark.parametrize("can_spawn", [False, True])
def test_the_new_role_scaffold_resolves_with_every_advanced_field_activated(
    tmp_path, can_spawn: bool
) -> None:
    """The new-role scaffold has no ruled example block — its advanced fields are individually
    commented — so activate those instead. Both ``can_spawn`` emissions are covered because
    ``--can-spawn`` swaps one line for another."""
    body = overrides._NEW_ROLE_SCAFFOLD_TPL.format(
        slug="security-expert",
        can_spawn_line=overrides._CAN_SPAWN_ACTIVE if can_spawn else overrides._CAN_SPAWN_COMMENTED,
    )
    activated = "\n".join(
        line[2:] if line.startswith("# ") and "=" in line else line for line in body.splitlines()
    )
    _write_override(tmp_path, "roles/security-expert.toml", activated + "\n")

    role = resolve_role("security-expert", tmp_path)

    assert role.slug == "security-expert"
    assert role.model == "sonnet"
    assert role.color == "teal"
    assert role.responsibilities and role.agreements
    assert role.can_spawn is can_spawn
