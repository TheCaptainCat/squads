"""Repo-hygiene gate: every override document kind resolves through the shared merge engine."""

import ast
from pathlib import Path

#: Loader module (relative to the repo root) -> the document it resolves. Every override kind
#: squads accepts belongs here; adding one without adding its entry is the drift this catches.
OVERRIDE_LOADERS: dict[str, str] = {
    "src/squads/_workflow/_loader.py": "the workflow spec (.overrides/workflow.toml)",
    "src/squads/_interactions/_loader.py": "the team playbook (.overrides/playbook.toml)",
    "src/squads/_roles/_loader.py": "the role catalog (.overrides/roles.toml)",
    "src/squads/_roles/_resolver.py": "a role (.overrides/roles/<slug>.toml)",
    "src/squads/_specload.py": "the load path the three whole-document loaders share",
}

#: The calls through which a loader reaches the merge engine: directly, or through the shared
#: load path that makes it.
_MERGE_ROUTES = frozenset({"merge_override", "load_override"})

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
        if not _MERGE_ROUTES & _called_names(_tree(rel))
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
    """A renamed or deleted loader must update this list, not shrink the scan's coverage."""
    root = _repo_root()
    missing = [rel for rel in OVERRIDE_LOADERS if not (root / rel).is_file()]
    assert not missing, f"listed override loader no longer exists: {missing}"
