import re

_BRACKET = re.compile(r"(\\*)\[")
_TRAILING_RUN = re.compile(r"\\+\Z")
_EMPTY_TAG_PAIR = "[bold][/bold]"


def escape_markup(text: str) -> str:
    """Escape ``text`` so Rich prints it byte for byte in any context.

    Every ``[`` becomes ``\\[``, which Rich reads the same whether or not a later ``]`` makes
    it look like a tag. A backslash run before a bracket, or at the end, is doubled and closed
    with an empty tag pair, so one copy prints whatever follows.
    """

    def bracket(match: re.Match[str]) -> str:
        run = match[1]
        return f"{run}{run}{_EMPTY_TAG_PAIR}\\[" if run else "\\["

    escaped = _BRACKET.sub(bracket, text)
    trailing = _TRAILING_RUN.search(escaped)
    if trailing is None:
        return escaped
    return f"{escaped}{trailing[0]}{_EMPTY_TAG_PAIR}"
