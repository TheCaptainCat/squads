"""An override the process cannot read (or, for the role catalog, cannot decode) is refused with
that document's own wording, whichever loader reads it."""

import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from squads._errors import SquadsError
from squads._interactions._loader import load_playbook
from squads._roles._catalog import get_catalog
from squads._roles._loader import load_role_catalog
from squads._workflow import bundled_spec, load_workflow_spec

_NO_PERMISSION_BITS = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="permission bits are not enforced for this user or platform",
)

type Loader = Callable[[Path], object]

_LOADERS: dict[str, tuple[Loader, str, str]] = {
    "workflow": (
        lambda squad_dir: load_workflow_spec(squad_dir=squad_dir),
        "workflow.toml",
        "Cannot read workflow override",
    ),
    "playbook": (
        lambda squad_dir: load_playbook(get_catalog(), bundled_spec(), squad_dir),
        "playbook.toml",
        "Cannot read playbook override",
    ),
    "roles": (
        lambda squad_dir: load_role_catalog(squad_dir),
        "roles.toml",
        "cannot read role catalog override",
    ),
}


@_NO_PERMISSION_BITS
@pytest.mark.parametrize("document", sorted(_LOADERS))
def test_an_unreadable_override_is_refused_in_the_documents_own_words(
    tmp_path: Path, document: str
) -> None:
    load, filename, expected = _LOADERS[document]
    override = tmp_path / ".overrides" / filename
    override.parent.mkdir()
    override.write_text("", encoding="utf-8")
    override.chmod(0)
    try:
        with pytest.raises(SquadsError, match=expected):
            load(tmp_path)
    finally:
        override.chmod(0o600)


def test_a_role_catalog_override_that_is_not_utf8_is_refused(tmp_path: Path) -> None:
    override = tmp_path / ".overrides" / "roles.toml"
    override.parent.mkdir()
    override.write_bytes(b"\xff\xfe")
    with pytest.raises(SquadsError, match="is not valid UTF-8"):
        load_role_catalog(tmp_path)


@pytest.mark.parametrize("document", sorted(_LOADERS))
def test_an_override_that_is_not_utf8_is_refused_without_the_codec_text(
    tmp_path: Path, document: str
) -> None:
    load, filename, _ = _LOADERS[document]
    override = tmp_path / ".overrides" / filename
    override.parent.mkdir()
    override.write_bytes(b"\xff\xfe")
    with pytest.raises(SquadsError, match="is not valid UTF-8") as refused:
        load(tmp_path)
    assert filename in str(refused.value)
    assert "codec" not in str(refused.value)
