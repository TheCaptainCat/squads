"""Repo-hygiene gate: every override document kind resolves through the shared merge engine.

Three documents are overridable — the workflow spec, the playbook, and a role — and the whole
point of ``squads._specmerge`` is that all three get the *same* semantics: splat-refs resolved
against the bundled base, a leaf-granular deep merge, a closed top-level key space, and the
``[selected]`` deselect refused where it has no meaning. A loader that hand-rolls its own merge
instead gets none of that, and it gets it silently: the document still loads, so nothing
downstream reports the difference.

That is not hypothetical. The role resolver assigned raw TOML values straight into a plain
dataclass — unknown keys discarded without a word, no typed validation, splat-refs never
resolved — so ``can_spawn = "false"`` was a truthy string that *granted* spawn authority and
``responsibilities = ["$(*self)", …]`` wrote the literal token into the generated agent
definition. Every one of those is a class the shared engine plus a typed model already handles
for the other two documents.

So this scan asserts the routing structurally, per loader: the module calls ``merge_override``,
and it does not define a merge of its own. Structural rather than behavioural on purpose — a
behavioural probe passes as soon as one path happens to be wired, while a fourth override kind
added later would sail past it.
"""

import ast
from pathlib import Path

#: Loader module (relative to the repo root) -> the document it resolves. Every override kind
#: squads accepts belongs here; adding one without adding its entry is the drift this catches.
OVERRIDE_LOADERS: dict[str, str] = {
    "src/squads/_workflow/_loader.py": "the workflow spec (.overrides/workflow.toml)",
    "src/squads/_interactions/_loader.py": "the team playbook (.overrides/playbook.toml)",
    "src/squads/_roles/_resolver.py": "a role (.overrides/roles/<slug>.toml)",
}

#: Names that would indicate a loader re-implementing what the engine owns. A loader may *call*
#: these; defining one of its own is the hand-rolled merge this forbids.
_ENGINE_FUNCTION_NAMES = frozenset({"deep_merge", "apply_selected", "resolve_splat_refs"})


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _tree(rel: str) -> ast.Module:
    return ast.parse((_repo_root() / rel).read_text(encoding="utf-8"))


def _called_names(tree: ast.Module) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def _defined_names(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }


def test_every_override_loader_merges_through_merge_override() -> None:
    missing = {
        rel: document
        for rel, document in OVERRIDE_LOADERS.items()
        if "merge_override" not in _called_names(_tree(rel))
    }
    assert not missing, (
        "an override document is resolved without the shared merge engine — it silently loses "
        "splat-refs, the closed top-level key space and typed validation: "
        f"{missing}"
    )


def test_no_override_loader_defines_its_own_merge_primitive() -> None:
    redefined = {
        rel: sorted(_defined_names(_tree(rel)) & _ENGINE_FUNCTION_NAMES)
        for rel in OVERRIDE_LOADERS
        if _defined_names(_tree(rel)) & _ENGINE_FUNCTION_NAMES
    }
    assert not redefined, (
        "a loader defines a merge primitive the shared engine already owns; two merges cannot "
        f"be kept in step, and the second one is the one nobody tests: {redefined}"
    )


def test_the_listed_loaders_all_exist() -> None:
    """Keeps the map honest: a renamed or deleted loader must update this list rather than
    quietly reducing the scan's coverage to whatever still happens to be on disk."""
    root = _repo_root()
    missing = [rel for rel in OVERRIDE_LOADERS if not (root / rel).is_file()]
    assert not missing, f"listed override loader no longer exists: {missing}"
