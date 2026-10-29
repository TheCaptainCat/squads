"""squads — manage a team of AI agents working on a code project."""

from functools import cache


@cache
def _installed_version() -> str:
    from importlib.metadata import version

    return version("squads")


def __getattr__(name: str) -> str:
    """``__version__``, read from the installed metadata on first use."""
    if name == "__version__":
        return _installed_version()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def version_line() -> str:
    """The line ``--version`` prints."""
    return f"squads {_installed_version()}"
