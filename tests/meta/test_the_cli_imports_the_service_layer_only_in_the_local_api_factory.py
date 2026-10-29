"""The CLI imports `squads._services` in one place, the factory that builds the local API, so no
renderer or command can call the service.

Imports are read as absolute module names: relative imports resolved against their package, and
`importlib.import_module`/`__import__` with a string literal counted as an import."""

from tests._import_scan import SRC, imports_of, names_any

CLI_DIR = SRC / "_cli"
SERVICES = ("squads._services",)

#: The one function allowed to import the service layer: (module, function).
FACTORY = ("_calls.py", "local_api")


def _offenders() -> dict[str, list[int]]:
    offenders: dict[str, list[int]] = {}
    for path in sorted(CLI_DIR.rglob("*.py")):
        rel = path.relative_to(CLI_DIR).as_posix()
        lines = sorted(
            {
                i.line
                for i in imports_of(path)
                if names_any(i.module, SERVICES) and (rel, i.function) != FACTORY
            }
        )
        if lines:
            offenders[rel] = lines
    return offenders


def test_only_the_local_api_factory_imports_the_service_layer() -> None:
    offenders = _offenders()
    assert not offenders, (
        f"these CLI modules import squads._services outside {FACTORY[1]}() in {FACTORY[0]}; "
        f"call the operation through the Api instead: {offenders}"
    )


def test_the_scan_finds_the_import_in_the_factory() -> None:
    module, function = FACTORY
    found = imports_of(CLI_DIR / module)
    assert any(names_any(i.module, SERVICES) and i.function == function for i in found)
