"""A 0.16 squad is stamped 0.17 by ``sq migrate up`` with no item file changed, and until then the
schema gate asks for ``sq migrate up``.

One table: which command runs on the 0.16 squad, and what the gate and the stamp then show.
"""

import hashlib
import shutil
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.anyio

_CORPUS = Path(__file__).parent.parent / "fixtures" / "corpus" / "v0_16"


def _hashes(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.md"))
    }


def _stamp(root: Path) -> str:
    return tomllib.loads((root / ".squads.toml").read_text(encoding="utf-8"))["schema_version"]


#: row -> (command, exit code, text in the output, stamp afterwards)
_ROWS: dict[str, tuple[list[str], int, str, str]] = {
    "list-is-refused": (["list"], 1, "sq migrate up", "0.16"),
    "migrate-up": (["migrate", "up"], 0, "0.17", "0.17"),
}


@pytest.mark.parametrize("row", list(_ROWS))
async def test_the_gate_asks_for_migrate_up_and_the_migration_writes_no_item_file(
    row: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invoke
) -> None:
    root = tmp_path / "squad"
    shutil.copytree(_CORPUS, root)
    monkeypatch.chdir(root)
    before = _hashes(root)
    args, code, needle, stamp = _ROWS[row]

    result = await invoke(args)

    assert result.exit_code == code, result.output
    assert needle in result.output
    assert _stamp(root) == stamp
    assert _hashes(root) == before
