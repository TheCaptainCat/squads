"""Every ``sq create`` door refuses an empty ``--parent`` instead of quietly dropping it.

The option was tested for truthiness rather than for presence, so ``--parent ""`` took the
no-parent branch: the command created the item with no parent, printed ``created <ID>`` and
exited 0. Nothing is corrupted -- a parentless item is a legitimate corpus state -- but a
caller who supplied a parent gets an item without one and is told the command worked, so the
only way to notice is to read the item back. A script or an agent interpolating an id that
resolves to empty loses the hierarchy edge silently.

Three create commands carried the identical expression, so the resolution now lives in one
shared helper and these tests drive all three: the statically-registered built-in types, the
lazily-built custom types declared in an override, and ``guide`` (its own command, extra
options).

The remedy in the message is deliberately *not* the update door's. ``update`` says
``use --no-parent``; ``create`` has no such flag, because omitting ``--parent`` is how a
parentless item is made. Both doors lead with the same sentence, which is asserted below --
naming a flag that does not exist on this door would be worse than saying nothing.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from _helpers import create_item

pytestmark = pytest.mark.anyio

#: A custom work type declared purely in an override, to reach the lazily-built create
#: command -- the same generic path a built-in type takes, via a different builder.
_CUSTOM_TYPE_TOML = """\
[items.incident]
prefix = "INC"
folder = "incidents"
lifecycle = "work"
parents = ["epic"]
aliases = ["inc"]
order = 66
category = "work"
"""


def _declare_custom_type(squad_dir: Path) -> None:
    override_dir = squad_dir / ".overrides"
    override_dir.mkdir(parents=True, exist_ok=True)
    (override_dir / "workflow.toml").write_text(_CUSTOM_TYPE_TOML, encoding="utf-8")


def _one_line(output: str) -> str:
    """Collapse the captured render to one line so an assertion survives console wrapping."""
    return " ".join(output.split())


async def _corpus(invoke) -> list[dict[str, Any]]:
    """Every item, read back through the CLI.

    Not through the ``svc`` fixture: that ``Service`` was built before the override below
    declared the custom type, so its spec no longer describes the corpus it would read.
    ``invoke`` resolves the active spec per call, which is also what a real ``sq`` run does.
    """
    listed = await invoke(["list", "-a", "--json"])
    assert listed.exit_code == 0, listed.output
    return json.loads(listed.output)


async def _ids(invoke) -> set[str]:
    return {row["id"] for row in await _corpus(invoke)}


# Each entry is the create command's own argv tail: the type word plus whatever options that
# door requires beyond --parent. Parametrising over the doors is the point -- a fix applied to
# one site and not the others passes a single-door test.
_DOORS = [
    pytest.param(["create", "feature", "Built-in door"], id="builtin-type"),
    pytest.param(["create", "incident", "Custom door"], id="custom-type"),
    pytest.param(["create", "guide", "Guide door"], id="guide"),
]


@pytest.mark.parametrize("argv", _DOORS)
@pytest.mark.parametrize("empty", ["", "   "], ids=["empty", "whitespace-only"])
async def test_an_empty_parent_is_refused_and_creates_nothing(project, invoke, argv, empty):
    _declare_custom_type(project.squad_dir)
    before = await _ids(invoke)

    result = await invoke([*argv, "--author", "manager", "--parent", empty])

    assert result.exit_code != 0, result.output
    assert "created" not in result.output
    assert "--parent needs an item ID" in _one_line(result.output)
    # Refused by the option guard, not by the id parser failing further down: the parser
    # answers about a token ("no item with number ..."), this answers about the flag.
    assert "no item with number" not in _one_line(result.output)
    assert await _ids(invoke) == before


@pytest.mark.parametrize("argv", _DOORS)
async def test_the_refusal_names_no_flag_the_create_door_does_not_have(project, invoke, argv):
    _declare_custom_type(project.squad_dir)

    result = await invoke([*argv, "--author", "manager", "--parent", ""])

    text = _one_line(result.output)
    # The update door's remedy, copied verbatim, would point at a flag `sq create` never
    # accepts. Its absence is the assertion; `--parent` itself is named instead.
    assert "--no-parent" not in text
    assert "omit --parent" in text


@pytest.mark.parametrize("argv", _DOORS)
async def test_omitting_parent_still_creates_a_parentless_item(project, invoke, argv):
    _declare_custom_type(project.squad_dir)

    result = await invoke([*argv, "--author", "manager"])

    assert result.exit_code == 0, result.output
    new = [row for row in await _corpus(invoke) if row["title"] == argv[2]]
    assert len(new) == 1, result.output
    assert new[0]["parent"] is None


@pytest.mark.parametrize(
    "type_word",
    [pytest.param("feature", id="builtin-type"), pytest.param("incident", id="custom-type")],
)
async def test_a_real_parent_still_resolves_in_full_and_bare_number_forms(
    project, svc, invoke, type_word
):
    _declare_custom_type(project.squad_dir)
    epic = (await create_item(svc, "epic", "Epic")).item

    full = await invoke(
        ["create", type_word, "Full form", "--author", "manager", "--parent", epic.id]
    )
    assert full.exit_code == 0, full.output

    bare = await invoke(
        ["create", type_word, "Bare form", "--author", "manager", "--parent", str(epic.sequence_id)]
    )
    assert bare.exit_code == 0, bare.output

    parents = {
        row["title"]: row["parent"]
        for row in await _corpus(invoke)
        if row["title"] in {"Full form", "Bare form"}
    }
    assert parents == {"Full form": epic.id, "Bare form": epic.id}


async def test_the_create_and_update_doors_lead_with_the_same_refusal(svc, invoke):
    """The shared half of the two messages, pinned so the doors cannot drift apart again.

    Only the leading sentence is shared: the remedy after the semicolon is per-door, because
    the way to end up without a parent differs between creating an item and editing one.
    """
    epic = (await create_item(svc, "epic", "Epic")).item
    feat = (await create_item(svc, "feature", "Feature", parent=epic.id)).item

    created = await invoke(["create", "feature", "Refused", "--author", "manager", "--parent", ""])
    updated = await invoke(["feature", str(feat.sequence_id), "update", "--parent", ""])

    assert created.exit_code != 0, created.output
    assert updated.exit_code != 0, updated.output
    shared = "--parent needs an item ID"
    assert shared in _one_line(created.output)
    assert shared in _one_line(updated.output)
    # ... and the remedies stay different, each naming something its own door accepts.
    assert "--no-parent" in _one_line(updated.output)
    assert "--no-parent" not in _one_line(created.output)
