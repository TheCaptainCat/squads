"""``effective_dir``: the process directory joined with every ``-C`` value in order, resolved
physically. An absolute value replaces what came before it, an empty value changes nothing, and
``..`` after a symbolic link steps out of the link's target rather than out of the link's parent.
"""

from pathlib import Path

import pytest

from squads._cli._common import effective_dir, help_requested


@pytest.fixture
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    base = (tmp_path / "base").resolve()
    for sub in ("a/b/c", "elsewhere/inner", "target/deep"):
        (base / sub).mkdir(parents=True)
    (base / "link").symlink_to(base / "target" / "deep", target_is_directory=True)
    monkeypatch.chdir(base)
    return base


_ROWS = {
    "no values": ([], "."),
    "one relative": (["a"], "a"),
    "absolute": (["{abs}"], "{abs}"),
    "absolute resets what came before": (["a", "{abs}", "inner"], "{abs}/inner"),
    "empty changes nothing": (["a", "", "b"], "a/b"),
    "empty alone": ([""], "."),
    "chain of three": (["a", "b", "c"], "a/b/c"),
    "dot segments and a trailing slash": (["a/./b/"], "a/b"),
    "dotdot": (["a/b", ".."], "a"),
    "dotdot after a link, as two values": (["link", ".."], "target"),
    "dotdot after a link, as one value": (["link/.."], "target"),
}


@pytest.mark.parametrize("row", _ROWS)
def test_the_effective_directory_joins_the_values_in_order(row: str, cwd: Path) -> None:
    values, expected = _ROWS[row]
    absolute = str(cwd / "elsewhere")
    values = [v.format(abs=absolute) for v in values]
    expected_path = (cwd / expected.format(abs=absolute)).resolve()

    assert effective_dir(values) == expected_path


def test_a_link_in_the_chain_is_resolved_physically(cwd: Path) -> None:
    assert effective_dir(["link"]) == cwd / "target" / "deep"


_NOT_HELP = {
    "-C consumes the next token": ["-C", "--help", "list"],
    "the value of -C after another -C": ["-C", "a", "-C", "--help"],
}


@pytest.mark.parametrize("row", _NOT_HELP)
def test_a_help_spelled_as_the_value_of_c_is_not_a_help_request(row: str) -> None:
    assert not help_requested(_NOT_HELP[row])


def test_help_after_c_is_a_help_request() -> None:
    assert help_requested(["-C", "a", "--help"])
