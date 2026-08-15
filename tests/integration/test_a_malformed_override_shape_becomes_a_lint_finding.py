"""``sq workflow lint`` reports a malformed override *shape* as a finding, at every section and
nesting position, and never as a traceback.

The loader walked the merged mapping assuming every section, every entry and every inline array
was the shape the grammar declares. TOML is happy to produce otherwise: ``items = "oops"`` and
``[items] task = "oops"`` both parse, and both escaped as a raw ``AttributeError`` /
``TypeError`` carrying internal file paths — out of ``sq list``, out of ``sq check``, and out of
``sq workflow lint``, whose own contract is that it never raises and captures every error as a
finding. The one diagnostic an adopter has died on precisely the input it exists to diagnose.

Table-driven over shape x position rather than one case per branch, because the original gap
was never a missing branch — it was an assumption repeated at eight sites, and a single example
per site would have been written from the same assumption. Only ``statuses`` and ``roles``
degraded cleanly before, and only because those two happened to call ``model_validate`` before
touching the data; that accident is what the table is written against.
"""

from pathlib import Path

import pytest

from squads import __version__

pytestmark = pytest.mark.anyio

#: (id, override body). Every entry is well-formed TOML that parses fine and is the wrong SHAPE
#: for the grammar — a section that is not a table, an entry that is not a table, an array that
#: is not an array, an array element that is not a table, at every position the walk touches.
_MALFORMED_SHAPES: list[tuple[str, str]] = [
    ("items_section_is_a_string", 'items = "oops"'),
    ("items_section_is_an_int", "items = 3"),
    ("items_entry_is_a_string", '[items]\ntask = "oops"'),
    ("items_entry_is_an_array", "[items]\ntask = []"),
    ("statuses_section_is_a_string", 'statuses = "oops"'),
    ("statuses_entry_is_an_int", "[statuses]\nDraft = 1"),
    ("lifecycles_section_is_an_array", "lifecycles = []"),
    ("lifecycles_entry_is_a_string", '[lifecycles]\nwork = "oops"'),
    ("lifecycles_initial_is_an_int", "[lifecycles.work]\ninitial = 5"),
    ("collections_section_is_a_string", 'collections = "oops"'),
    ("collections_entry_is_a_float", "[collections]\npriority = 1.5"),
    ("collection_badges_is_a_string", '[collections.priority]\nbadges = "x"'),
    ("collection_badge_element_is_a_string", '[collections.priority]\nbadges = ["x"]'),
    ("subentity_kinds_section_is_a_bool", "subentity_kinds = true"),
    ("subentity_kinds_entry_is_an_int", "[subentity_kinds]\nstory = 7"),
    ("subentity_kind_fields_is_a_string", '[subentity_kinds.story]\nfields = "x"'),
    ("roles_section_is_a_string", 'roles = "oops"'),
    ("roles_entry_is_an_array", "[roles]\nactive = []"),
    ("item_parents_is_a_string", '[items.task]\nparents = "feature"'),
    ("item_fields_is_a_string", '[items.task]\nfields = "oops"'),
    ("item_fields_element_is_a_string", '[items.task]\nfields = ["oops"]'),
    ("item_ref_rules_is_a_string", '[items.task]\nref_rules = "oops"'),
    ("item_ref_rules_element_is_a_string", '[items.task]\nref_rules = ["oops"]'),
    ("item_aliases_element_is_an_int", "[items.task]\naliases = [1]"),
]


def _write_override(squad_dir: Path, content: str) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(
        f"# squads:override-base:{__version__}\n{content}\n", encoding="utf-8"
    )


@pytest.mark.parametrize(("case", "body"), _MALFORMED_SHAPES, ids=[c for c, _ in _MALFORMED_SHAPES])
async def test_lint_reports_the_shape_rather_than_raising(project, invoke, case, body) -> None:
    import tomllib

    # The fixture must be VALID TOML — otherwise this measures the parser's refusal, not the
    # loader's shape handling, and the case proves nothing about the walk.
    tomllib.loads(body)
    _write_override(project.squad_dir, body)

    result = await invoke(["workflow", "lint"])

    # A clean refusal exits through typer.Exit (recorded as SystemExit); anything else is the
    # raw walk error escaping, which is the whole defect.
    assert isinstance(result.exception, SystemExit), (
        f"{case} escaped as {type(result.exception).__name__}: {result.exception!r}"
    )
    assert result.exit_code == 1, result.output
    assert "Traceback" not in result.output
    assert "workflow spec errors" in result.output


@pytest.mark.parametrize(("case", "body"), _MALFORMED_SHAPES, ids=[c for c, _ in _MALFORMED_SHAPES])
async def test_an_ordinary_command_refuses_cleanly_on_the_same_shape(
    project, invoke, case, body
) -> None:
    """The same table through a command that opens a service: the refusal is the shared
    override refusal, not a traceback, and it still points at the diagnostic."""
    _write_override(project.squad_dir, body)

    result = await invoke(["list"])

    assert isinstance(result.exception, SystemExit), (
        f"{case} escaped as {type(result.exception).__name__}: {result.exception!r}"
    )
    assert result.exit_code != 0
    assert "sq workflow lint" in result.output


async def test_the_finding_names_the_offending_path_not_just_the_section(project, invoke) -> None:
    """A shape refusal is only actionable if it says *where*: a nested entry must be named as
    ``items.task``, not reported against the whole ``items`` table."""
    _write_override(project.squad_dir, '[items]\ntask = "oops"')

    result = await invoke(["workflow", "lint"])

    assert "items.task" in result.output.replace("\n", "").replace(" ", "")


@pytest.mark.parametrize(
    ("body", "container"),
    [
        ('[items.task]\nfields = "oops"', "fields"),
        ('[items.task]\nref_rules = "oops"', "ref_rules"),
        ('[collections.priority]\nbadges = "oops"', "badges"),
        ('[subentity_kinds.story]\nfields = "oops"', "fields"),
    ],
)
async def test_a_string_where_an_array_belongs_is_reported_as_the_container_not_its_letters(
    project, invoke, body: str, container: str
) -> None:
    """A string is iterable, so a walk with no shape guard does not crash on one — it iterates
    the *characters*. ``fields = "oops"`` then validates ``"o"`` as a field and reports
    ``field[0]``, an index into a value that has no elements at all. That is a refusal, so
    "did not raise" cannot tell the two apart; what distinguishes them is that the guarded
    version names the container and the shape it should have, and never invents an element
    index for a value that is not a sequence of elements.
    """
    from squads._workflow._loader import lint_workflow_spec

    _write_override(project.squad_dir, body)

    # Read the findings directly rather than the rendered table: the console truncates the
    # location column, and the claim here is about the finding's text, not its layout.
    findings = lint_workflow_spec(project.squad_dir)

    assert len(findings) == 1, findings
    _level, _location, message, _hint = findings[0]
    assert f"{container} must be an array" in message, message
    assert "[0]" not in message, f"invented a per-element index for a non-array value: {message}"


async def test_a_declared_ref_rule_kind_outside_the_vocabulary_is_refused(project, invoke) -> None:
    """The declared-seam half of the ref-rule gap: a rule for a kind no ref surface accepts can
    never fire, so it is a declaration that silently does nothing. Refused at load, with the
    accepted set named. The vocabulary itself is unchanged — this validates against it."""
    _write_override(project.squad_dir, '[items.task]\nref_rules = [{ kind = "supersedez" }]')

    result = await invoke(["workflow", "lint"])

    assert result.exit_code == 1
    flat = result.output.replace("\n", "").replace(" ", "")
    assert "supersedez" in flat
    assert "supersedes" in flat  # the accepted set is listed, so the typo is fixable in place


@pytest.mark.parametrize(
    "body",
    [
        # A `records` type: its bundle turns on `supersedes_incoming`, so the rule it declares
        # is one a validator actually acts on.
        pytest.param('[items.guide]\nref_rules = [{ kind = "supersedes" }]', id="records_type"),
        # A `work` type declaring a rule no validator is defined over — nothing to be
        # unreachable, so the reachability clause has no opinion about it.
        pytest.param('[items.epic]\nref_rules = [{ kind = "fixes" }]', id="unenforced_kind"),
    ],
)
async def test_a_declared_ref_rule_for_a_real_kind_still_loads(project, invoke, body) -> None:
    """The control: the check must refuse the undeclared *kind*, not ref_rules in general.

    Written against a type whose category can enforce the rule it declares. `supersedes` is
    the one ref kind a validator is defined over (`supersedes_incoming`, in the `records`
    bundle and nowhere else), so declaring it on a `work` type is separately refused by the
    category-consistency clause that guards that validator's reachability — a real refusal,
    not this one, and pinning it here would have made this control assert the wrong thing.
    """
    _write_override(project.squad_dir, body)

    result = await invoke(["workflow", "lint"])

    assert result.exit_code == 0, result.output
