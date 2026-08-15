"""A workflow override that will not resolve is refused everywhere, never answered from the
bundled vocabulary the project did not declare.

The failure this pins was asymmetric and undetectable from outside. With one bad key in the
override, ``sq list`` exited 1 naming the error while ``sq workflow types``, ``statuses``,
``collections``, ``roles`` and the cheatsheet all exited 0 and described the *bundled* spec —
the project's own declared type absent from every one of them. A client cannot tell that apart
from a correct answer: exit 0, a well-formed payload, empty stderr. The catalog surfaces are
the only honest answer to "what types do I have", so answering them from a spec that failed to
load is worse than not answering at all.

Two things must survive the refusal, and both are asserted here rather than assumed:
``sq workflow lint`` (the diagnostic — refusing it would leave no way to see what is wrong) and
``sq --help`` (a question about ``sq``, not about this squad).
"""

from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

#: Declares a type the bundled spec has never heard of AND breaks one key, so a surface that
#: answers from bundled vocabulary is caught twice over: by the exit code, and by the absence of
#: `widget` from a payload that claims to enumerate this project's types.
_DECLARES_WIDGET_AND_BREAKS_A_ROLE = (
    '[items.widget]\nprefix = "WDG"\nfolder = "widgets"\nlifecycle = "work"\n\n'
    '[roles.active]\nsettled = false\nhidden = false\ncolor = "not-a-real-intent"\nlive = true\n'
)


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}", encoding="utf-8"
    )
    # Load it eagerly: a fixture that is broken in a way the test did not intend (a TOML syntax
    # error, say) would otherwise read as the very refusal under test and prove nothing.
    from squads._errors import SquadsError
    from squads._workflow._loader import load_workflow_spec

    with pytest.raises(SquadsError, match="not-a-real-intent"):
        load_workflow_spec(squad_dir=squad_dir)


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["workflow", "types", "--json"], id="types_json"),
        pytest.param(["workflow", "types"], id="types_table"),
        pytest.param(["workflow", "statuses", "--json"], id="statuses"),
        pytest.param(["workflow", "collections", "--json"], id="collections"),
        pytest.param(["workflow", "roles", "--json"], id="roles"),
        pytest.param(["workflow", "subentity-kinds", "--json"], id="subentity_kinds"),
        pytest.param(["workflow"], id="cheatsheet"),
        pytest.param(["workflow", "--raw"], id="cheatsheet_raw"),
        pytest.param(["list"], id="list"),
    ],
)
async def test_no_surface_answers_from_the_bundled_spec(project, invoke, argv: list[str]) -> None:
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(argv)

    assert result.exit_code != 0, f"{argv} answered instead of refusing: {result.output}"
    # And it did not answer from bundled vocabulary on the way out.
    assert "epic" not in result.output or "widget" in result.output


async def test_the_refusal_names_the_file_the_cause_and_the_action(project, invoke) -> None:
    """A hard stop that does not say what to fix is a worse defect than the quiet wrong answer
    it replaces — so the three things needed to act are pinned, not just the exit code."""
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(["workflow", "types", "--json"])
    output = result.output

    assert "workflow.toml" in output  # which file (the path may be console-wrapped)
    assert "not-a-real-intent" in output  # what is actually wrong, at key level
    assert "sq workflow lint" in output  # what to do, and what still runs


async def test_the_service_layer_and_the_read_surfaces_give_the_same_refusal(
    project, invoke
) -> None:
    """One failure must not read as two problems: the message a command that opens a service
    prints and the message a spec-reading catalog prints are the same text."""
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    from_service = await invoke(["list"])
    from_catalog = await invoke(["workflow", "types", "--json"])

    marker = "could not be loaded"
    assert marker in from_service.output and marker in from_catalog.output


async def test_workflow_lint_still_runs_and_diagnoses(project, invoke) -> None:
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(["workflow", "lint"])

    assert result.exit_code == 1
    assert "not-a-real-intent" in result.output


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["create", "task", "X", "--author", "manager"], id="create_type"),
        pytest.param(["task", "1", "update", "--priority", "high"], id="update_type"),
    ],
)
async def test_the_refusal_never_escapes_as_a_traceback_from_a_parse_time_hook(
    project, invoke, argv: list[str]
) -> None:
    """`sq create <type>` and `sq <type> <n> update` re-derive `--priority`'s help from the
    active spec inside Click's own `get_params`, which runs *before* the command body and so
    outside the boundary that turns a SquadsError into a clean message. Once the spec started
    refusing, that hook escaped as a wall of Python — the one outcome the refusal contract rules
    out. The help refresh is presentation, so it degrades; the refusal comes from the body.
    """
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(argv)

    assert result.exit_code != 0
    assert "Traceback" not in result.output
    assert "could not be loaded" in result.output


async def test_a_help_page_still_renders_while_the_spec_refuses(project, invoke) -> None:
    """The other side of that degradation: `--help` answers a question about the command, not
    about the squad, so it must keep working with whatever help text was baked in."""
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(["create", "task", "--help"])

    assert result.exit_code == 0, result.output
    assert "Traceback" not in result.output


async def test_root_help_still_renders(project, invoke) -> None:
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(["--help"])

    assert result.exit_code == 0
    assert "Usage" in result.output


# --------------------------------------------------------------- the command table itself


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["widget", "1", "show"], id="declared_type_leaf"),
        pytest.param(["create", "widget", "third"], id="declared_type_create"),
        pytest.param(["widget", "--help"], id="declared_type_help"),
        pytest.param(["nonsense"], id="a_name_nothing_declares"),
    ],
)
async def test_the_command_table_refuses_instead_of_denying_the_type_exists(
    project, invoke, argv: list[str]
) -> None:
    """The last surface answering from bundled vocabulary was the parser. A name the static
    table does not carry got resolved against the *bundled* spec — the fallback that keeps the
    parser from raising — found absent, and handed to Click, which exits 2 with
    `No such command 'widget'`. For a squad whose own override declares `widget`, that is a
    claim about this squad's vocabulary made from a document this squad did not declare, and it
    sends the adopter to check their spelling rather than the file that failed to load.

    `nonsense` is in the table deliberately: while the override is unresolvable, sq cannot know
    whether any given word is a declared type, so "no such command" is unsupportable for every
    unclassifiable name, not just the one that happens to be declared.
    """
    _write_override(project.squad_dir, _DECLARES_WIDGET_AND_BREAKS_A_ROLE)

    result = await invoke(argv)

    assert result.exit_code == 1, result.output
    assert "could not be loaded" in result.output
    assert "No such command" not in result.output


async def test_a_typo_on_a_healthy_squad_still_gets_no_such_command(project, invoke) -> None:
    """The control that keeps the refusal honest in the other direction. With the spec loading
    fine, sq *can* answer "that is not a type here" — and must, or every mistyped command on
    every healthy squad would blame an override that is not there."""
    result = await invoke(["nonsense"])

    assert result.exit_code == 2, result.output
    assert "No such command" in result.output


async def test_a_squad_with_a_valid_override_still_answers_with_its_own_vocabulary(
    project, invoke
) -> None:
    """The control. The refusal must be caused by the *failure*, not by the mere presence of an
    override — without this, a bug that refused every overriding squad would pass every test
    above."""
    override_dir = project.squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n"
        '[items.widget]\nprefix = "WDG"\nfolder = "widgets"\nlifecycle = "work"\n',
        encoding="utf-8",
    )

    result = await invoke(["workflow", "types", "--json"])

    assert result.exit_code == 0, result.output
    assert "widget" in result.output
