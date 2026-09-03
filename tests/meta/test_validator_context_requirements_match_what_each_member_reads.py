"""Repo-hygiene gate: every catalog validator's declared context requirements are exactly the
call-path-dependent context its own body reads.

Two fields of ``ValidatorContext`` depend on which call path built it — ``raw_text`` and
``type_present`` — and ``ValidatorEngine.gate()`` carries neither. Before this gate existed the
consequence was invisible: the gate handed those fields their empty values, every reader guarded
itself into returning nothing, and a member that had been designed to sit the gate out looked
exactly like one that had never been considered on it. One error-level member was in the second
group, so it blocked no create or update on any door while its level said it would, and the
engine carried a comment asserting that no such member existed.

So the declaration is the mechanism and this is what holds it to the code:

1. Those fields are read **only** inside catalog members (and inside the accessor that reports
   which of them a context carries). A helper taking the context and reading one on a member's
   behalf would put the read where the per-member scan below cannot see it, and the declaration
   would go stale with nothing failing.
2. Each member's declaration equals what its body reads. A member added tomorrow that reads the
   item's text fails here until it says so — at which point the fact that it cannot gate is on
   the record next to its registration, rather than three call frames away in a sentinel.

Static, because the property is about what the code says rather than about one run of it: a
behavioural test can only observe the members that happen to exist today.
"""

import ast
from pathlib import Path
from typing import Any, cast

from squads._services._validators import CATALOG, VALIDATOR_CONTEXT, ContextRequirement

_SOURCE = ("src", "squads", "_services", "_validators.py")

#: Functions allowed to read a call-path-dependent field without being catalog members. One
#: entry, and it is the accessor whose whole subject is which of them a context carries.
_NON_MEMBER_READERS = frozenset({"held_context"})

_FIELDS = frozenset(r.value for r in ContextRequirement)


def _module_ast() -> ast.Module:
    path = Path(__file__).resolve().parents[2].joinpath(*_SOURCE)
    return ast.parse(path.read_text(encoding="utf-8"))


def _reads_by_function(tree: ast.Module) -> dict[str, frozenset[str]]:
    """Map every function in the module to the call-path-dependent fields its body reads.

    Attribute name only, deliberately: matching ``ctx.raw_text`` by receiver would miss the
    same read reached through any other binding, and this module names the parameter ``ctx``
    only by convention.
    """
    out: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        read = {
            child.attr
            for child in ast.walk(node)
            if isinstance(child, ast.Attribute)
            and isinstance(child.ctx, ast.Load)
            and child.attr in _FIELDS
        }
        if read:
            out.setdefault(node.name, set()).update(read)
    return {name: frozenset(fields) for name, fields in out.items()}


def _member_function_names() -> dict[str, str]:
    """Catalog name -> the name of the function registered under it.

    ``Validator`` is a call-only Protocol, so the function's own ``__name__`` is not part of
    the declared interface — cast to read it, rather than widen the Protocol for a test.
    """
    return {name: cast(Any, fn).__name__ for name, fn in CATALOG.items()}


def test_call_path_dependent_context_is_read_only_inside_catalog_members() -> None:
    reads = _reads_by_function(_module_ast())
    assert reads, "the scan found no reads at all — it has stopped matching anything"

    allowed = set(_member_function_names().values()) | _NON_MEMBER_READERS
    strays = sorted(set(reads) - allowed)

    assert not strays, (
        f"{strays} read call-path-dependent context outside a catalog member. A read reached "
        "through a helper is invisible to the per-member declaration below, so the declaration "
        "would go stale silently — read the field in the member itself, or make the helper a "
        "catalog member with its own declaration."
    )


def test_each_member_declares_exactly_the_context_it_reads() -> None:
    reads = _reads_by_function(_module_ast())
    functions = _member_function_names()
    assert len(functions) == len(CATALOG) > 1, "the catalog resolved to too few members to scan"

    mismatched: dict[str, tuple[set[str], set[str]]] = {}
    for name, fn_name in functions.items():
        actual = set(reads.get(fn_name, frozenset()))
        declared = {r.value for r in VALIDATOR_CONTEXT.get(name, frozenset())}
        if actual != declared:
            mismatched[name] = (actual, declared)

    assert not mismatched, (
        "VALIDATOR_CONTEXT disagrees with what these members read "
        f"(name: reads / declared) — {mismatched}. A member reading context the gate does not "
        "carry never runs there; declaring it is what keeps that fact reviewable instead of "
        "leaving an error-level member silently gating nothing."
    )
