"""The client side of the command endpoint, on the standard library alone.

It holds the environment variables a served command can see; the daemon reads the same list, so
the two sides cannot disagree on it.
"""

#: The variables the client sends with a command, absent ones left out. A variable outside this
#: list does not exist for a served command; the daemon's diagnostic variables are never on it.
SENT_ENVIRONMENT: tuple[str, ...] = (
    "SQUADS_SESSION_ID",
    "SQUADS_PARENT_SESSION_ID",
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
