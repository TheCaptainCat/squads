"""The import scan reports a name taken from a package that re-exports it as the module defining
it, so a guard that names an inner module sees an import however it is spelled."""

from tests._import_scan import imports_in, names_any


def _modules(source: str) -> set[str]:
    return {i.module for i in imports_in(source, "squads._probe")}


def test_a_re_exported_name_is_reported_as_its_defining_module() -> None:
    found = _modules("from squads._workflow import bundled_spec\n")

    assert "squads._workflow._bundled" in found
    assert "squads._workflow._bundled.bundled_spec" in found


def test_a_name_re_exported_through_two_packages_is_followed_to_the_end() -> None:
    found = _modules("from squads._cli import main\n")

    assert {"squads._cli._entry", "squads._cli._app"} <= found


def test_a_name_the_package_does_not_re_export_adds_nothing() -> None:
    assert _modules("from squads._workflow import not_there\n") == {
        "squads._workflow",
        "squads._workflow.not_there",
    }


def test_the_defining_module_matches_a_guard_prefix() -> None:
    found = _modules("from squads._cli import app\n")

    assert any(names_any(m, ("squads._cli._app",)) for m in found)
