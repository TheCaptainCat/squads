"""Repo-hygiene gate: wherever ``normalize_model`` discards a value, ``model_drop_warning``
reports it — the two are called from the same function or neither is.

``normalize_model`` maps any model name outside the four Claude Code accepts to ``None``, and
the pointer template omits ``model:`` when it is ``None``. That is a total function with no
error channel: the declaration is in the role item's frontmatter, durable and readable, while
the generated ``.claude/agents/<slug>.md`` has no model line and the agent runs on the session
default. Nothing printed, ``sq check`` clean. An adopter has no way to find out except by
diffing a generated file against a declaration and knowing to look.

The pairing is the contract. ``normalize_model`` answers "can this host render it"; the
warning answers "and here is what I just failed to render". Splitting them is what produced
the silence, so a call site that takes the first answer without the second is the exact
regression this forbids.

Deliberately a pairing rule and not "validate the value earlier": the upstream refusal already
exists for role *overrides* and must stay the only refusal, so the two never disagree about
one value. Everything else that can set a model reports here instead.
"""

import ast
from pathlib import Path

_NORMALIZER = "normalize_model"
_REPORTER = "model_drop_warning"

#: The tree scanned — every backend, not just the one that defines the pair today: a second
#: backend rendering the same field would reach for the same normalizer.
_SCANNED = Path("src") / "squads" / "_backends"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _called_names(func: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def _unpaired_call_sites() -> list[str]:
    root = _repo_root() / _SCANNED
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path.name == "_frontmatter.py":
            continue  # where both are defined; a definition is not a call site
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            called = _called_names(func)
            if _NORMALIZER in called and _REPORTER not in called:
                offenders.append(f"{path.relative_to(_repo_root())}::{func.name}")
    return offenders


def test_no_call_site_normalizes_a_model_without_reporting_the_drop() -> None:
    offenders = _unpaired_call_sites()
    assert not offenders, (
        f"{offenders} call {_NORMALIZER}() without {_REPORTER}() — an unrenderable model would "
        "vanish from the generated pointer with nothing said. Return the warning on the "
        "Artifact the write already returns."
    )


def test_the_pair_still_exists_to_be_paired() -> None:
    """Guards against the silent way this stops guarding: if the reporter is deleted, every
    call site trivially satisfies "no unpaired normalizer" by there being nothing to pair."""
    source = (
        _repo_root() / "src" / "squads" / "_backends" / "_claude_code" / "_frontmatter.py"
    ).read_text(encoding="utf-8")
    assert f"def {_NORMALIZER}" in source
    assert f"def {_REPORTER}" in source
