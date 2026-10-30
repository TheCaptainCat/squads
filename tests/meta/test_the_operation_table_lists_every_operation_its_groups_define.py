"""Repo-hygiene gate: the operation table names every operation its group modules define, once,
in the group that defines it, and asking for one operation imports no other group."""

import importlib
import pkgutil
import subprocess
import sys

import squads._api as api_package
from squads._api import _ops
from squads._api._api import Operation


def _defined() -> dict[str, str]:
    """Each operation constant of each group module, with the group it is defined in."""
    found: dict[str, str] = {}
    for info in pkgutil.iter_modules(api_package.__path__):
        if not info.name.startswith("_ops_"):
            continue
        module = importlib.import_module(f"squads._api.{info.name}")
        for name, value in vars(module).items():
            if isinstance(value, Operation):
                assert name not in found, f"{name} is defined in two groups"
                found[name] = info.name.removeprefix("_ops_")
    return found


def test_the_table_lists_each_defined_operation_once_in_its_group() -> None:
    defined = _defined()
    assert sorted(_ops._ORDER) == sorted(defined), "the table order and the groups disagree"
    assert len(set(_ops._ORDER)) == len(_ops._ORDER)
    listed = {name: group for group, names in _ops._GROUPS for name in names}
    assert listed == defined


def test_asking_for_one_operation_imports_only_its_group() -> None:
    probe = (
        "import sys\nfrom squads._api import _ops\n_ops.BOARD_LIST\n"
        "print(sorted(m for m in sys.modules if m.startswith('squads._api._ops_')))"
    )
    done = subprocess.run(
        [sys.executable, "-I", "-c", probe], capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "['squads._api._ops_board']"
