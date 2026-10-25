import sys

from squads import version_line


def main() -> None:
    """Console-script entry point. A bare ``--version`` is answered here, before the CLI and
    everything it imports load; every other invocation goes to ``squads._cli.main``."""
    if sys.argv[1:] == ["--version"]:
        from rich.console import Console

        Console().print(version_line())
        return
    from squads._cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
