"""An unknown key inside a *nested* override section is refused the way an unknown key at the
document's top level already is: naming the key, where it sits, the accepted keys for that
section, and the running version.

The gap this pins was one of depth, not of kind. A closed top-level key space refuses with a
sentence an adopter can act on; the nested key space is closed by the same argument and used to
refuse with pydantic's own validation error verbatim — no version, an internal model class in
the header, an ``input_value``/``input_type`` dump, and a link to pydantic's error
documentation rather than to anything about squads. Same promise, two dialects, and only the
shallow one kept it.

Two precedents were available and they disagree, so the choice is pinned here rather than left
to the next reader: the top-level-key and ref-kind refusals both name the offending name *and*
list the accepted set, while the unknown-validator refusal names the entry alone. The first
shape is the one asserted below — a menu is what turns "not accepted" into a next action.

Driven through the loaders and the CLI, never through the exception type: what an adopter reads
is the message, and a test that asserts on ``ValidationError`` would have passed throughout the
defect.
"""

from pathlib import Path
from typing import Any

import pytest

from squads import __version__
from squads._errors import SquadsError
from squads._interactions._loader import load_playbook
from squads._interactions._models import ItemPlaybookSpec, RoleGuideSpec
from squads._roles._loader import load_role_catalog
from squads._roles._models import RoleSpec
from squads._workflow._loader import load_workflow_spec
from squads._workflow._models import ItemSpec, LabelSpec

pytestmark = pytest.mark.anyio

#: Every leak an adopter-facing refusal must not carry. `extra_forbidden` and the pydantic link
#: are pydantic's vocabulary for our own rule; the `input_` dumps echo the adopter's value back
#: at them instead of naming the key; the model names are internal classes no override document
#: mentions.
_LEAKS = (
    "extra_forbidden",
    "input_value",
    "input_type",
    "errors.pydantic.dev",
    "validation error for",
    "ItemSpec",
    "RoleSpec",
    "LabelSpec",
    "ItemPlaybookSpec",
    "RoleGuideSpec",
)


def _write(squad_dir: Path, name: str, content: str) -> None:
    target = squad_dir / ".overrides" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# squads:override-base:{__version__}\n{content}", encoding="utf-8")


def _load_workflow(squad_dir: Path) -> None:
    load_workflow_spec(squad_dir=squad_dir)


def _load_catalog(squad_dir: Path) -> None:
    load_role_catalog(squad_dir=squad_dir)


def _load_playbook(squad_dir: Path) -> None:
    load_playbook(load_role_catalog(squad_dir=squad_dir), squad_dir=squad_dir)


#: One row per override document that can carry a nested section, each with the model whose
#: fields are the menu that document's refusal must offer. Three documents, because a fix proven
#: on one is exactly how the shallow half of this promise came to be kept and the deep half not.
_NESTED_CASES: list[tuple[str, str, str, str, str, Any]] = [
    (
        "workflow_item",
        "workflow.toml",
        "[items.task]\nbogus_key = 1\n",
        "bogus_key",
        "",
        ItemSpec,
    ),
    (
        "workflow_labels",
        "workflow.toml",
        '[items.task.labels]\ndeep_bogus = "x"\n',
        "deep_bogus",
        "labels",
        LabelSpec,
    ),
    (
        "roles_catalog_entry",
        "roles.toml",
        '[[roles]]\nslug = "manager"\nbogus_cat = 1\n',
        "bogus_cat",
        "",
        RoleSpec,
    ),
    (
        "playbook_type",
        "playbook.toml",
        "[types.task]\nbogus_pb = 1\n",
        "bogus_pb",
        "",
        ItemPlaybookSpec,
    ),
    (
        "playbook_role_guide",
        "playbook.toml",
        '[[types.task.roles]]\nslug = "qa"\nbogus_guide = 1\n',
        "bogus_guide",
        "",
        RoleGuideSpec,
    ),
]

_LOADERS = {
    "workflow.toml": _load_workflow,
    "roles.toml": _load_catalog,
    "playbook.toml": _load_playbook,
}


@pytest.mark.parametrize(
    ("document", "body", "key", "section", "model"),
    [pytest.param(*case[1:], id=case[0]) for case in _NESTED_CASES],
)
async def test_a_nested_unknown_key_is_named_with_its_menu_and_version(
    project, document: str, body: str, key: str, section: str, model: Any
) -> None:
    _write(project.squad_dir, document, body)

    with pytest.raises(SquadsError) as caught:
        _LOADERS[document](project.squad_dir)
    message = str(caught.value)

    assert f"unknown key {key!r}" in message
    if section:
        # The section the key actually sits in, not the parent that was being validated.
        assert f"in {section!r}" in message
    assert f"in v{__version__}" in message
    # The menu is the model's own field list, read off the model rather than restated here, so
    # this stays true when a field is added to it.
    assert str(sorted(model.model_fields)) in message


@pytest.mark.parametrize(
    ("document", "body"),
    [pytest.param(case[1], case[2], id=case[0]) for case in _NESTED_CASES],
)
async def test_no_override_refusal_leaks_its_validation_library(
    project, document: str, body: str
) -> None:
    """Asserted as a property over every override loader's refusal, not spot-checked on one
    input — one input is how the nested half of this went unnoticed the first time."""
    _write(project.squad_dir, document, body)

    with pytest.raises(SquadsError) as caught:
        _LOADERS[document](project.squad_dir)
    message = str(caught.value)

    leaked = [leak for leak in _LEAKS if leak in message]
    assert not leaked, f"refusal leaked {leaked}: {message}"


async def test_the_refusal_reaches_the_adopter_through_the_cli(project, invoke) -> None:
    """The loader is where the message is built; the command line is where it is read."""
    _write(project.squad_dir, "workflow.toml", "[items.task]\nbogus_key = 1\n")

    result = await invoke(["list"])

    assert result.exit_code != 0
    assert "unknown key 'bogus_key'" in result.output
    assert f"in v{__version__}" in result.output
    assert not [leak for leak in _LEAKS if leak in result.output]


async def test_a_top_level_unknown_key_still_refuses_in_its_own_shape(project) -> None:
    """The shallow half of the promise is untouched: it keeps the wording it already had, so
    folding the deep half in cannot have been done by rewriting the one that worked."""
    (project.squad_dir / ".overrides" / "roles").mkdir(parents=True, exist_ok=True)
    (project.squad_dir / ".overrides" / "roles" / "manager.toml").write_text(
        f"# squads:override-base:{__version__}\nnonsense = 1\n", encoding="utf-8"
    )

    from squads._roles._resolver import resolve_role

    with pytest.raises(SquadsError) as caught:
        resolve_role("manager", project.squad_dir)
    message = str(caught.value)

    assert "unknown top-level key 'nonsense'" in message
    accepted = sorted(set(RoleSpec.model_fields) | {"selected"})
    assert f"use one of the accepted top-level keys in v{__version__}: {accepted}" in message


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param('[items.task]\nprefix = 1\nfolder = "t"\n', "prefix", id="wrong_type"),
        pytest.param("[collections.nonsense]\n", "badges", id="missing_required"),
    ],
)
async def test_another_validation_failure_shape_is_left_exactly_as_it_was(
    project, body: str, expected: str
) -> None:
    """The fold is bounded to unknown keys. A wrong type and a missing required field keep the
    handling they have today — still refused, still naming the field, and deliberately not
    paraphrased by a formatter built to describe a different failure."""
    _write(project.squad_dir, "workflow.toml", body)

    with pytest.raises(SquadsError) as caught:
        _load_workflow(project.squad_dir)

    assert expected in str(caught.value)
