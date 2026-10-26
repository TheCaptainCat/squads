"""``sq role <slug> show``'s definition pane, when the role's base does not resolve.

A role no catalog entry, template or stored definition backs materialises from what its item
stores. The catalog card and the definition pane both render that, which looks like a resolved
definition, so the pane carries its own signal that the base is missing: otherwise an operator
has no way to tell a genuinely resolved role from one reading its own bare fields.
"""

import pytest

pytestmark = pytest.mark.anyio


async def test_a_resolvable_custom_role_prints_no_advisory(project, svc, invoke) -> None:
    """Control: a role that defines itself gets no advisory at all."""
    await svc.add_role(
        "custom-analyst",
        name="Sam Custom",
        job_title="custom role",
        description="A project-defined role.",
        mission="Do the custom thing.",
    )

    r = await invoke(["role", "custom-analyst", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "could not be resolved" not in r.output


async def test_a_role_with_no_backing_definition_prints_the_advisory(project, svc, invoke) -> None:
    await svc.create(
        "role",
        "Sam Custom",
        description="A project-defined role.",
        slug="custom-analyst",
        author="custom-analyst",
    )

    r = await invoke(["role", "custom-analyst", "show", "--raw"])

    assert r.exit_code == 0, r.output
    assert "Sam Custom" in r.output
    assert "could not be resolved" in r.output
    assert "sq check" in r.output
