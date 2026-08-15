"""The category-consistency refusal reaches the adopter on every gate, and the constraint it
protects is the one that used to die silently.

The unit tests pin the rule against the loader. This pins the two things only an end-to-end run
can show: that all three gates now agree (they were `sq list` exit 0, `sq workflow lint` "no
errors or warnings" and `sq check` exit 0 on a spec whose own declaration was unreachable), and
the behaviour underneath — `parent_required` was dead in *both* directions, so neither creating
with the declared parent nor creating without one honoured what the spec still reported.

Each fixture is gated on a control run first. A broken override used to leave `sq workflow …`
answering at exit 0 from the bundled spec, which is exactly how a sweep of this area produced
two false "silent fallback" results before it was caught; asserting the clean case first is what
makes the dirty case's exit code mean something.
"""

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

_TASK_TO_RECORDS = '[items.task]\ncategory = "records"\n'


def _write_override(squad_dir, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def test_all_three_gates_agree_where_all_three_were_silent(project, invoke) -> None:
    clean = await invoke(["list"])
    assert clean.exit_code == 0, clean.output  # the control: this squad is fine as it stands

    _write_override(project.squad_dir, _TASK_TO_RECORDS)

    assert (await invoke(["list"])).exit_code != 0
    assert (await invoke(["workflow", "lint"])).exit_code == 1
    assert (await invoke(["check"])).exit_code != 0


async def test_the_lint_finding_names_the_type_and_the_unreachable_declaration(
    project, invoke
) -> None:
    _write_override(project.squad_dir, _TASK_TO_RECORDS)

    from squads._workflow._loader import lint_workflow_spec

    # Read the findings rather than the rendered table: the console wraps and truncates, and
    # the claim here is about the finding's text.
    findings = lint_workflow_spec(project.squad_dir)
    messages = " ".join(message for _level, _loc, message, _hint in findings)

    assert "'task'" in messages
    assert "parent_required='feature'" in messages
    assert "subentity_kind 'subtask'" in messages


async def test_the_declaration_that_used_to_die_silently_is_what_the_stop_protects(
    project, svc, invoke
) -> None:
    """The behaviour underneath, driven rather than asserted — and narrower than first reported.

    What the reassignment actually killed is the `parents` allowlist: `sq create task --parent
    FEAT-n` succeeds against the bundled spec and is refused as "task takes no parent" once
    `task` is a record, while the loaded spec goes on reporting `parents=['feature']`. So the
    type declares which parents it accepts and accepts none of them.

    The *other* half of the reported consequence does not hold, and saying so matters more than
    restating it: creating a task with no parent succeeds **before and after** the move, because
    `parent_required` is not a create gate at all — it is read by `subtask_story_mapping` and for
    hint text. That is a separate, older property of `parent_required`, not something this
    reassignment introduced, and not what this refusal is for. Making a parent *mandatory* is its
    own opt-in (`parent_present`), pinned in
    `test_a_mandatory_parent_is_enforced_only_where_it_is_asked_for`; the assertion below is
    deliberately unchanged by it, because the bundled spec does not opt in.
    """
    epic = (await svc.create("epic", "An epic", author="manager")).item
    feature = (await svc.create("feature", "A feature", author="manager", parent=epic.id)).item

    # Against the bundled spec: the declared parent is accepted.
    with_parent = await invoke(
        ["create", "task", "Child", "--author", "manager", "--parent", feature.id]
    )
    assert with_parent.exit_code == 0, with_parent.output
    # …and a parentless task is accepted too — parent_required gates nothing here.
    assert (await invoke(["create", "task", "Orphan", "--author", "manager"])).exit_code == 0

    # With the contradictory reassignment, the load stops rather than letting the squad run on a
    # `parents` list that can no longer be satisfied.
    _write_override(project.squad_dir, _TASK_TO_RECORDS)
    refused = await invoke(
        ["create", "task", "Child again", "--author", "manager", "--parent", feature.id]
    )
    assert refused.exit_code != 0
    assert "workflow" in refused.output.lower()


async def test_a_reassignment_that_silences_nothing_is_still_allowed(project, invoke) -> None:
    """Reassignment is permitted; the guardrail is validation, not prohibition. `bug` declares
    no parent, no `parent_required` and no `subentity_kind`, so moving it loses nothing."""
    _write_override(project.squad_dir, '[items.bug]\ncategory = "records"\n')

    assert (await invoke(["list"])).exit_code == 0
    assert (await invoke(["workflow", "lint"])).exit_code == 0

    created = await invoke(["create", "bug", "Still creatable", "--author", "manager"])
    assert created.exit_code == 0, created.output
