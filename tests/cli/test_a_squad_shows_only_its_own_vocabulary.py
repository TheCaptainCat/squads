"""One scenario on whichever squad the run is on: create, add a mapped entry, list, tree, import,
help and the generated skill show the squad's own vocabulary and no word the other squad has and
this one drops.
"""

import json
import re
from pathlib import Path

import pytest

from squads._workflow import bundled_spec
from squads._workflow._loader import load_workflow_spec
from tests._profile import selected
from tests.meta import _vocabulary as vocabulary

pytestmark = pytest.mark.anyio

P = selected()
_CATEGORIES = (vocabulary.REF, vocabulary.KIND, vocabulary.TYPE, vocabulary.FIELD)
_TOKEN = re.compile(r"(?<![\w-])(?:--(?:no-|min-)?|add-)?([A-Za-z][\w-]*)")


def _write_events() -> Path:
    event = {"op": "create", "type": P.ref, "title": "Imported", "parent": str(2), "as": "manager"}
    path = Path("events.jsonl")
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")
    return path


async def _run(invoke, args: list[str]) -> str:
    result = await invoke(args)
    assert result.exit_code == 0, result.output
    return result.output


def _flag(code: str) -> str:
    return code.replace("_", "-")


async def _surfaces(invoke) -> dict[str, str]:
    """The text the scenario makes the CLI print, by where it came from."""
    flag = f"--{_flag(P.badge)}"
    created = await _run(
        invoke,
        [
            "create",
            P.ref,
            "Wire it",
            "--author",
            "manager",
            "--parent",
            str(2),
            flag,
            P.badge_value,
        ],
    )
    number = re.search(r"-(\d+)", created)
    assert number, created
    ref = str(number.group(1))
    added = await _run(
        invoke,
        [P.ref, ref, f"add-{P.kind}", "Step", f"--{_flag(P.target_kind)}", f"{P.target_prefix}1"],
    )
    events = _write_events()
    return {
        "create output": created,
        "add output": added,
        "list": await _run(invoke, ["list"]),
        "list --json": await _run(invoke, ["list", "--json"]),
        "tree --json": await _run(invoke, ["tree", "--json"]),
        "show --json": await _run(invoke, [P.ref, ref, "show", "--json"]),
        "import": await _run(invoke, ["import", str(events), "--dry-run"]),
        "create --help": await _run(invoke, ["create", P.ref, "--help"]),
        "update --help": await _run(invoke, [P.ref, ref, "update", "--help"]),
        "add --help": await _run(invoke, [P.ref, ref, f"add-{P.kind}", "--help"]),
        "list --help": await _run(invoke, ["list", "--help"]),
        "tree --help": await _run(invoke, ["tree", "--help"]),
    }


def _dropped(squad_dir: Path) -> vocabulary.Vocabulary:
    kept = vocabulary.vocabulary(load_workflow_spec(squad_dir), *_CATEGORIES)
    bundled = vocabulary.vocabulary(bundled_spec(), *_CATEGORIES)
    return vocabulary.dropped(bundled, kept)


def _spelled(text: str, names: vocabulary.Vocabulary) -> list[str]:
    """The tokens of *text* that are a name in *names* by themselves, as a flag, as a verb or as a
    key; English words that merely equal a badge code are not tokens of this kind."""
    quoted_keys = set(re.findall(r'"([\w-]+)":', text))
    flags = {m.group(1) for m in re.finditer(r"(?<![\w-])(?:--(?:no-|min-)?|add-)([\w-]+)", text)}
    return sorted((quoted_keys | flags) & set(names))


@pytest.mark.covers("create <type>", "--<field>", "--parent")
@pytest.mark.covers("<type> add-<kind>", "--<target-kind>")
@pytest.mark.covers("list", "--json")
@pytest.mark.covers("tree", "--json")
@pytest.mark.covers("<type> show", "--json")
@pytest.mark.covers("import", "file")
async def test_the_scenario_prints_the_squads_own_vocabulary_and_no_dropped_word(
    populated_project, invoke
) -> None:
    surfaces = await _surfaces(invoke)
    kept = f"--{_flag(P.badge)}"
    assert kept in surfaces["create --help"]
    assert f"add-{P.kind}" in await _run(invoke, [P.ref, "3", "--help"])
    assert f"--{_flag(P.target_kind)}" in surfaces["add --help"]
    assert await _run(invoke, [P.host_alias, "2", "show", "--json"])

    dropped = _dropped(populated_project.squad_dir)
    found = {where: _spelled(text, dropped) for where, text in surfaces.items()}

    assert {where: names for where, names in found.items() if names} == {}
