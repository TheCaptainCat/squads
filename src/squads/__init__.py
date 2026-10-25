"""squads — manage a team of AI agents working on a code project."""

from importlib.metadata import version

__version__ = version("squads")


def version_line() -> str:
    """The line ``--version`` prints."""
    return f"squads {__version__}"
