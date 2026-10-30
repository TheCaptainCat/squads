"""The client side of the command endpoint, on the standard library alone.

It holds the environment variables a served command can see; the daemon reads the same list, so
the two sides cannot disagree on it.
"""

#: The variables the client sends with a command, absent ones left out: every one that changes
#: what a command prints locally. The daemon's own environment answers for any other name.
SENT_ENVIRONMENT: tuple[str, ...] = (
    "SQUADS_SESSION_ID",
    "SQUADS_PARENT_SESSION_ID",
    "SQUADS_SPANS",
    "PY_COLORS",
    "GITHUB_ACTIONS",
    "TERMINAL_WIDTH",
    "_TYPER_FORCE_DISABLE_TERMINAL",
    "NO_COLOR",
    "FORCE_COLOR",
    "CLICOLOR_FORCE",
    "TTY_COMPATIBLE",
    "TTY_INTERACTIVE",
    "COLUMNS",
    "LINES",
    "TERM",
    "COLORTERM",
    "_SQ_COMPLETE",
    "_SQUADS_COMPLETE",
    "COMP_WORDS",
    "COMP_CWORD",
    "_TYPER_COMPLETE_ARGS",
    "_TYPER_COMPLETE_WORD_TO_COMPLETE",
    "_TYPER_COMPLETE_FISH_ACTION",
)
