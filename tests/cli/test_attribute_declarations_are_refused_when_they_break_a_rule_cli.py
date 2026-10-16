"""An override that declares attributes badly refuses every command at load: a table over the
refused shapes, each asserting exit 1, the named key, and that nothing was written. A second
table drives the pinned roster attributes through the loader, since an override can re-kind but
not delete a key the bundled spec declares."""

import pytest

from _helpers import squad_tree
from squads._errors import SquadsError
from squads._workflow._loader import (  # pyright: ignore[reportPrivateUsage]
    _build_spec,
    _bundled_raw,
)

pytestmark = pytest.mark.anyio

_COLLECTION_BADGE = '{ code = "impact", label = "Impact", collection = "priority" }'

#: (id, override text, fragments the refusal must carry)
REFUSALS = [
    *[
        (
            f"core-key-{key}",
            f'[items.guide.attributes]\n{key} = {{ kind = "str" }}\n',
            [f"'{key}'", "reserved"],
        )
        for key in ("status", "title", "slug", "refs", "created_at", "sequence_id")
    ],
    *[
        (
            f"json-added-{key}",
            f'[items.guide.attributes]\n{key} = {{ kind = "str" }}\n',
            [f"'{key}'", "reserved"],
        )
        for key in ("badges", "body", "discussion", "matched_subentities")
    ],
    *[
        (
            f"model-field-{key}",
            f'[items.guide.attributes]\n{key} = {{ kind = "str" }}\n',
            [f"'{key}'", "reserved"],
        )
        for key in ("path", "prefix", "extra")
    ],
    (
        "also-a-badge-code",
        '[items.guide]\nfields = [{ code = "priority", label = "Priority", collection = "priority" '
        f'}}, {_COLLECTION_BADGE}]\n\n[items.guide.attributes]\nimpact = {{ kind = "str" }}\n',
        ["'impact'", "field code"],
    ),
    (
        "a-badge-code-that-is-a-core-key",
        '[items.guide]\nfields = [{ code = "status", label = "S", collection = "priority" }]\n',
        ["'status'", "reserved"],
    ),
    (
        "an-unknown-kind",
        '[items.guide.attributes]\nweight = { kind = "float" }\n',
        ["kind"],
    ),
    (
        "extra-fields-is-not-read",
        '[items.guide]\nextra_fields = ["tags"]\n',
        ["extra_fields", "attributes"],
    ),
    (
        "a-pinned-role-attribute-with-another-kind",
        '[items.role.attributes]\nis_default = { kind = "str" }\n',
        ["'is_default'", "'bool'"],
    ),
    (
        "a-pinned-skill-attribute-with-another-kind",
        '[items.skill.attributes]\nwhen_to_use = { kind = "list" }\n',
        ["'when_to_use'", "'str'"],
    ),
]


@pytest.mark.parametrize(
    ("override", "fragments"), [r[1:] for r in REFUSALS], ids=[r[0] for r in REFUSALS]
)
async def test_a_bad_declaration_refuses_every_command_and_writes_nothing(
    project, invoke, override: str, fragments: list[str]
) -> None:
    (project.squad_dir / ".overrides").mkdir(exist_ok=True)
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(override, encoding="utf-8")
    before = squad_tree(project.root)

    result = await invoke(["list"])

    assert result.exit_code == 1, result.output
    for fragment in fragments:
        assert fragment in result.output
    assert squad_tree(project.root) == before


#: (id, roster type, pinned key removed, kind it is pinned with)
PINNED = [
    ("role-is-default", "role", "is_default", "bool"),
    ("role-is-dev", "role", "is_dev", "bool"),
    ("role-model", "role", "model", "str"),
    ("role-tech", "role", "tech", "str"),
    ("skill-allowed-tools", "skill", "allowed_tools", "str"),
    ("skill-model", "skill", "model", "str"),
    ("skill-when-to-use", "skill", "when_to_use", "str"),
]


@pytest.mark.parametrize(
    ("roster", "key", "kind"), [r[1:] for r in PINNED], ids=[r[0] for r in PINNED]
)
def test_a_roster_type_that_lacks_a_pinned_attribute_is_refused_naming_it(
    roster: str, key: str, kind: str
) -> None:
    raw = _bundled_raw()
    del raw["items"][roster]["attributes"][key]  # pyright: ignore[reportIndexIssue]

    with pytest.raises(SquadsError) as excinfo:
        _build_spec(raw)

    message = str(excinfo.value)
    assert f"'{key}'" in message
    assert f"'{kind}'" in message
    assert f"[items.{roster}.attributes]" in message


async def test_an_override_may_add_an_attribute_to_a_roster_type(project) -> None:
    override = '[items.role.attributes]\npronouns = { kind = "str" }\n'
    (project.squad_dir / ".overrides").mkdir(exist_ok=True)
    (project.squad_dir / ".overrides" / "workflow.toml").write_text(override, encoding="utf-8")

    from squads._workflow import load_workflow_spec

    spec = load_workflow_spec(squad_dir=project.squad_dir)

    assert spec.item_attributes("role")["pronouns"].kind == "str"
    assert "is_default" in spec.item_attributes("role")
