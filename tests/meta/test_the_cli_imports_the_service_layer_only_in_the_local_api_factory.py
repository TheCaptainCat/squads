"""The CLI imports `squads._services` in one place, the factory that builds the local API, so no
renderer or command can call the service. Modules whose commands are not on an operation yet are
listed as pending; the list only shrinks.

Imports are read as absolute module names: relative imports resolved against their package, and
`importlib.import_module`/`__import__` with a string literal counted as an import."""

from tests._import_scan import SRC, imports_of, names_any

CLI_DIR = SRC / "_cli"
SERVICES = ("squads._services",)

#: The one function allowed to import the service layer: (module, function).
FACTORY = ("_calls.py", "local_api")

#: CLI modules that still import the service layer, one per line, sorted.
PENDING = frozenset(
    {
        "_common.py",
        "_import.py",
        "_main.py",
    }
)


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


def test_only_the_local_api_factory_and_the_pending_modules_import_the_service_layer() -> None:
    offenders = _offenders()
    unexpected = {rel: lines for rel, lines in offenders.items() if rel not in PENDING}
    assert not unexpected, (
        f"these CLI modules import squads._services outside {FACTORY[1]}() in {FACTORY[0]}; "
        f"call the operation through the Api instead: {unexpected}"
    )


def test_every_pending_module_still_imports_the_service_layer() -> None:
    stale = PENDING - set(_offenders())
    assert not stale, f"no longer import squads._services; delete them from PENDING: {stale}"


def test_the_scan_finds_the_import_in_the_factory() -> None:
    module, function = FACTORY
    found = imports_of(CLI_DIR / module)
    assert any(names_any(i.module, SERVICES) and i.function == function for i in found)
