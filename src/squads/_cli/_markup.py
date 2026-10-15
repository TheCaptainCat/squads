import re

# A run of backslashes plus a `[`; the lookahead group is set when Rich would read it as a tag.
_BRACKET = re.compile(r"(\\*)\[((?=[a-z#/@][^\[]*?\]))?")
_TRAILING_RUN = re.compile(r"\\+\Z")
_EMPTY_TAG_PAIR = "[bold][/bold]"


def escape_markup(text: str) -> str:
    """Escape ``text`` so Rich prints it byte for byte in any context.

    Rich drops one backslash before every non-tag ``[`` on render, and a trailing backslash
    would join the markup that follows; the trailing run is doubled and closed with an empty
    tag pair, which prints a single copy whether plain text or a tag comes next.
    """

    def bracket(match: re.Match[str]) -> str:
        run = match[1]
        if match[2] is None:
            return f"{run}\\["
        return f"{run}{run}\\["

    escaped = _BRACKET.sub(bracket, text)
    trailing = _TRAILING_RUN.search(escaped)
    if trailing is None:
        return escaped
    return f"{escaped}{trailing[0]}{_EMPTY_TAG_PAIR}"
