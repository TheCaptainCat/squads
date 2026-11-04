"""Markdown helpers the converters share."""


def fenced(body: str, language: str = "") -> str:
    """*body* as a code block whose fence is longer than any backtick run inside it."""
    longest = current = 0
    for char in body:
        current = current + 1 if char == "`" else 0
        longest = max(longest, current)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{body}\n{fence}"
