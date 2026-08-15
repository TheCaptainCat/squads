"""`parent_required` names a type; making a parent *mandatory* is a separate, opt-in decision.

A type declaring `parent_required = "feature"` reads like a create-time constraint and is not
one: `sq create task` with no parent has always been accepted, and `sq check` has always been
clean afterwards. That gap is closed by naming what was missing rather than by changing what the
bundled spec does — `parents` is an eligibility allowlist ("a feature *or nothing*"), `no_parent`
forbids a parent outright, and neither can say "there must be one". `parent_present` says it, and
sits in no category bundle, so a type opts in.

Why it is opt-in rather than the `work` default is the load-bearing fact here, and the last test
drives it: one effective validator-name set backs both `ValidatorEngine.gate()` (create/update)
and `report()` (`sq check`), and `gate()` differs only by filtering to error level. There is no
position from which a check refuses a new parentless item while staying quiet about the
parentless items already on disk — so defaulting it on would not read as "new items need a
parent", it would read as "every historical bare item is now an error", with nothing a migration
could do about it.

The control runs first throughout. A squad whose bundled behaviour was already refusing would
make every refusal below meaningless.
"""

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

#: The opt-in, written the way an adopter would: extend `task`'s own validator list. Every other
#: field of the bundled `task` is inherited, `parent_required = "feature"` included.
_TASK_REQUIRES_A_PARENT = '[items.task]\nvalidators = ["parent_present"]\n'

#: The same opt-in on a type that declares no `parent_required` at all — the check is defined
#: over the *presence* of a parent, and the declared type only sharpens the message.
_BUG_REQUIRES_A_PARENT = '[items.bug]\nvalidators = ["parent_present"]\n'


def _write_override(squad_dir, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )


async def test_the_bundled_spec_still_accepts_a_task_with_no_parent(project, invoke) -> None:
    """The behaviour this change deliberately does not touch. `task` declares
    `parent_required = "feature"` in the document squads ships, and a bare `sq create task` is
    still valid — every squad that creates one keeps working across the upgrade."""
    created = await invoke(["create", "task", "Orphan", "--author", "manager"])
    assert created.exit_code == 0, created.output
    assert (await invoke(["check"])).exit_code == 0


async def test_naming_the_check_refuses_a_parentless_item_and_says_which_type(
    project, svc, invoke
) -> None:
    epic = (await svc.create("epic", "An epic", author="manager")).item
    feature = (await svc.create("feature", "A feature", author="manager", parent=epic.id)).item

    # Control: both shapes are accepted before the opt-in.
    assert (await invoke(["create", "task", "Bare", "--author", "manager"])).exit_code == 0

    _write_override(project.squad_dir, _TASK_REQUIRES_A_PARENT)

    refused = await invoke(["create", "task", "Bare again", "--author", "manager"])
    assert refused.exit_code != 0, refused.output
    assert "feature" in refused.output  # the declared parent_required, not a generic "a parent"

    # …and the declared parent is still accepted, so this is a requirement, not a prohibition.
    accepted = await invoke(
        ["create", "task", "Child", "--author", "manager", "--parent", feature.id]
    )
    assert accepted.exit_code == 0, accepted.output


async def test_the_check_stands_alone_on_a_type_that_declares_no_required_parent(
    project, svc, invoke
) -> None:
    """`bug` declares `parents = []` and no `parent_required`, so "any parent, or none" becomes
    "any parent". The message degrades to the generic wording rather than inventing a type."""
    epic = (await svc.create("epic", "An epic", author="manager")).item

    assert (await invoke(["create", "bug", "Free-floating", "--author", "manager"])).exit_code == 0

    _write_override(project.squad_dir, _BUG_REQUIRES_A_PARENT)

    refused = await invoke(["create", "bug", "Free again", "--author", "manager"])
    assert refused.exit_code != 0, refused.output
    assert "requires a parent" in refused.output

    attached = await invoke(
        ["create", "bug", "Attached", "--author", "manager", "--parent", epic.id]
    )
    assert attached.exit_code == 0, attached.output


async def test_the_bundled_default_is_off_because_the_gate_and_the_report_are_one_set(
    project, invoke
) -> None:
    """The reason this is opt-in, driven rather than argued.

    A parentless task created while the bundled spec was in force does not become invisible once
    the opt-in lands: the same name set that refuses the *next* create is what `sq check` runs
    over the whole corpus, so the item already on disk is reported too. That is the cost of
    turning this on by default, paid once per pre-existing bare item, and it is why the bundled
    document leaves it off.
    """
    created = await invoke(["create", "task", "Legacy orphan", "--author", "manager"])
    assert created.exit_code == 0, created.output
    assert (await invoke(["check"])).exit_code == 0  # control: clean before the opt-in

    _write_override(project.squad_dir, _TASK_REQUIRES_A_PARENT)

    checked = await invoke(["check"])
    assert checked.exit_code != 0, checked.output
    assert "TASK-" in checked.output


async def test_the_declaration_was_never_inert_it_was_enforced_somewhere_else(
    project, svc, invoke
) -> None:
    """What `parent_required` does on the bundled spec, with no opt-in anywhere: it resolves the
    host whose stories a subtask may map onto, and that resolution refuses. Dropping the field as
    an unread declaration would have cost this — and the refusal names the declared type, which
    is the part `parents` (a multi-valued allowlist) could not have supplied."""
    task = (await svc.create("task", "Orphan with a subtask", author="manager")).item
    await svc.add_subtask(task.id, "map me")

    number = task.id.split("-")[-1]
    refused = await invoke(["task", number, "subtask", "ST1", "update", "--story", "US1"])
    assert refused.exit_code != 0, refused.output
    assert "feature" in refused.output
