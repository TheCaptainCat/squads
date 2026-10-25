"""One table: how often one invocation reads and builds each spec document, for every document
(workflow, roles, playbook) absent, present or broken, and for every command family.

The rule per document: the packaged file is read at most once, the project override file is
opened and parsed at most once, and the bundled model and the merged model are each built at most
once (one build in all with the document not overridden). A bare ``--version`` loads nothing.

Every row runs the real entry point in a fresh interpreter. The probe counts opens of any
``.overrides/<document>.toml`` at the file level, parses of that text, reads of the packaged
files and calls of each model builder (bundled or merged), so a read that bypasses the shared
load path is counted as well. The ``refused``
shape is a workflow override that conflicts with a live task, so ``list`` is refused and
``check``/``repair`` run through their fallbacks. The ``check`` row runs over a roster of several
roles, the case where catalog reads would scale with the roster.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from _helpers import make_service
from squads import __version__
from squads._services import _service as service

#: Counts one invocation's document loads, before the package is imported. ``read`` is an open of
#: ``.overrides/<document>.toml``, ``packaged`` a read of the packaged file, ``build`` a model
#: built from either. Written to stderr as JSON once the entry point has returned.
_PROBE = """\
import builtins, io, json, sys, threading
from collections import Counter

counts = Counter()
BUILDERS = {
    ("_workflow/_loader.py", "_build_spec"): "workflow",
    ("_roles/_loader.py", "_build_catalog"): "roles",
    ("_interactions/_loader.py", "_build_spec"): "playbook",
}
DOCUMENTS = {"workflow.toml": "workflow", "roles.toml": "roles", "playbook.toml": "playbook"}

real_open = io.open


def counting_open(file, *args, **kwargs):
    path = str(file).replace("\\\\", "/")
    parts = path.split("/")
    if len(parts) > 1 and parts[-2] == ".overrides" and parts[-1] in DOCUMENTS:
        counts[DOCUMENTS[parts[-1]] + ".read"] += 1
    return real_open(file, *args, **kwargs)


io.open = counting_open
builtins.open = counting_open

import tomllib

override_texts = {text: name for name, text in json.loads(sys.argv[2]).items()}
real_loads = tomllib.loads


def counting_loads(text, *args, **kwargs):
    if text in override_texts:
        counts[override_texts[text] + ".parse"] += 1
    return real_loads(text, *args, **kwargs)


tomllib.loads = counting_loads


def profile(frame, event, arg):
    if event != "call":
        return
    code = frame.f_code
    name, path = code.co_name, code.co_filename
    if "/squads/" not in path:
        return
    if path.endswith("/_specload.py") and name == "bundled_bytes":
        document = DOCUMENTS.get(getattr(frame.f_locals.get("document"), "bundled_file", ""))
        counts[f"{document}.packaged"] += 1
    for (suffix, builder), document in BUILDERS.items():
        if name == builder and path.endswith(suffix):
            caller = frame.f_back
            names, local = caller.f_code.co_name, caller.f_locals
            if document == "workflow":
                merged = names != "_load_bundled_spec"
            elif document == "roles":
                merged = local.get("loaded") is not None
            else:
                merged = local.get("squad_dir") is not None
            counts[f"{document}.build." + ("merged" if merged else "bundled")] += 1


sys.setprofile(profile)
threading.setprofile_all_threads(profile)
from squads.__main__ import main

sys.argv = ["sq", *json.loads(sys.argv[1])]
try:
    main()
    exit_code = 0
except SystemExit as stop:
    exit_code = stop.code or 0
sys.setprofile(None)
sys.stderr.write(json.dumps({"exit": exit_code, **counts}))
"""

_STAMP = f"# squads:override-base:{__version__}\n"
_DOCUMENTS = ("workflow", "roles", "playbook")
_FILES = {"workflow": "workflow.toml", "roles": "roles.toml", "playbook": "playbook.toml"}

#: A valid override of each document on its own, and a broken one.
_VALID = {
    "workflow": '[items.incident]\nprefix = "INC"\nfolder = "incidents"\nlifecycle = "guide"\n',
    "roles": "",
    "playbook": '[types.task]\noverview = "Overridden."\n',
}
_BROKEN = "[broken\nnot toml ==="
#: Stand-ins for an override file holding undecodable bytes and one the process may not open.
_NOT_UTF8 = "\0not-utf8"
_UNREADABLE = "\0unreadable"
_DIRECTORY = "\0directory"
_CANNOT_CHMOD = sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0)
#: With all three present the playbook may name the type the workflow override declares.
_ALL_VALID = {
    **_VALID,
    "playbook": (
        '[types.incident]\noverview = "An incident."\nlifecycle = "Draft -> Active"\n'
        'commands = ["sq create incident"]\nroles = [{ slug = "qa", authors = true }]\n'
    ),
}
#: Shrinks the priority codes under the template squad's urgent task: the index check refuses.
_REFUSED = (
    '[collections.priority]\nlabel = "Priority"\n'
    'badges = [{ code = "high", label = "High" }, { code = "low", label = "Low" }]\n'
)


def _shapes() -> dict[str, dict[str, str]]:
    shapes: dict[str, dict[str, str]] = {
        "none": {},
        "all": _ALL_VALID,
        "refused": {"workflow": _REFUSED},
    }
    for document in _DOCUMENTS:
        shapes[f"{document}-present"] = {document: _VALID[document]}
        shapes[f"{document}-broken"] = {document: _BROKEN}
        shapes[f"{document}-not-utf8"] = {document: _NOT_UTF8}
        shapes[f"{document}-unreadable"] = {document: _UNREADABLE}
        shapes[f"{document}-directory"] = {document: _DIRECTORY}
    return shapes


_SHAPES = _shapes()
_COMMANDS = {
    "help": ["--help"],
    "read": ["list"],
    "check": ["check"],
    "sync": ["sync"],
    "repair": ["repair"],
    "lint": ["workflow", "lint"],
    "adopt": ["adopt"],
}


@pytest.fixture(scope="module")
def template_squad(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A squad of eight roles and a developer with two tasks, one of them urgent."""
    root = tmp_path_factory.mktemp("loads-template")

    async def build() -> None:
        paths = (await service.init(root=root, roles_spec="all")).paths
        svc = make_service(paths)
        await svc.create("task", "Probe", author="manager")
        await svc.create("task", "Urgent", author="manager", priority="urgent")

    asyncio.run(build())
    return root


def _run(root: Path, argv: list[str], texts: dict[str, str]) -> dict[str, int]:
    done = subprocess.run(
        [sys.executable, "-c", _PROBE, json.dumps(argv), json.dumps(texts)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "Traceback" not in done.stderr, done.stdout + done.stderr
    return json.loads(done.stderr[done.stderr.rindex("{") :])


def _check(seen: dict[str, int], shape: dict[str, str]) -> None:
    for document in _DOCUMENTS:
        bundled = seen.get(f"{document}.build.bundled", 0)
        merged = seen.get(f"{document}.build.merged", 0)
        assert seen.get(f"{document}.packaged", 0) <= 1, (document, seen)
        assert seen.get(f"{document}.read", 0) <= 1, (document, seen)
        assert seen.get(f"{document}.parse", 0) <= 1, (document, seen)
        assert bundled <= 1, (document, seen)
        assert merged <= 1, (document, seen)
        # A merged model exists only for a document that is overridden. A playbook beside a
        # workflow override is built once for the merged spec, with no bundled playbook beside it.
        assert bundled + merged <= (2 if document in shape else 1), (document, seen)


def test_a_bare_version_loads_no_document(tmp_path: Path) -> None:
    seen = _run(tmp_path, ["--version"], {})

    assert seen["exit"] == 0
    assert not [key for key in seen if "." in key], seen


@pytest.mark.parametrize("command", list(_COMMANDS))
@pytest.mark.parametrize("shape_name", list(_SHAPES))
def test_each_document_is_loaded_at_most_once_per_invocation(
    shape_name: str, command: str, template_squad: Path, tmp_path: Path
) -> None:
    shape = _SHAPES[shape_name]
    if _UNREADABLE in shape.values() and _CANNOT_CHMOD:
        pytest.skip("permission bits are not enforced for this user or platform")
    root = tmp_path / "squad"
    shutil.copytree(template_squad, root)
    unreadable: list[Path] = []
    for document, body in shape.items():
        override = root / "squads" / ".overrides" / _FILES[document]
        override.parent.mkdir(parents=True, exist_ok=True)
        if body == _NOT_UTF8:
            override.write_bytes(b"\xff\xfe")
        elif body == _DIRECTORY:
            override.mkdir()
        elif body == _UNREADABLE:
            override.write_text("", encoding="utf-8")
            override.chmod(0)
            unreadable.append(override)
        else:
            override.write_text(_STAMP + body, encoding="utf-8")
    if command == "adopt":
        (root / ".squads.toml").unlink()

    texts = {
        document: _STAMP + body
        for document, body in shape.items()
        if body not in (_NOT_UTF8, _UNREADABLE, _DIRECTORY)
    }
    try:
        seen = _run(root, _COMMANDS[command], texts)
    finally:
        for override in unreadable:
            override.chmod(0o600)

    _check(seen, shape)
